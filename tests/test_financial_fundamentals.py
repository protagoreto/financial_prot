from datetime import date

import pytest

from src.db import connect, initialize_database
from src.financial_fundamentals import (
    build_financial_fundamental_growth_snapshot,
    build_financial_fundamental_snapshot,
)
from src.ingestion import get_or_create_company
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.repository import insert_financial_record


REQUIRED = (
    (FinancialMetric.REVENUE, StatementType.INCOME_STATEMENT),
    (
        FinancialMetric.NET_INTEREST_INCOME,
        StatementType.INCOME_STATEMENT,
    ),
    (
        FinancialMetric.NET_INCOME,
        StatementType.INCOME_STATEMENT,
    ),
    (FinancialMetric.EPS, StatementType.PER_SHARE),
    (
        FinancialMetric.SHARES_OUTSTANDING,
        StatementType.PER_SHARE,
    ),
    (FinancialMetric.EQUITY, StatementType.BALANCE_SHEET),
    (
        FinancialMetric.TANGIBLE_BOOK_VALUE,
        StatementType.BALANCE_SHEET,
    ),
    (
        FinancialMetric.TOTAL_ASSETS,
        StatementType.BALANCE_SHEET,
    ),
    (
        FinancialMetric.NET_LOANS,
        StatementType.BALANCE_SHEET,
    ),
)


def add_period(
    connection,
    company_id,
    period_end,
    publication_date,
    values,
):
    for metric, statement_type in REQUIRED:
        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=statement_type,
                metric=metric,
                value=values[metric],
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
            ),
        )


def build_database(tmp_path):
    path = tmp_path / "financial.sqlite"
    initialize_database(path)

    connection = connect(path)

    company_id = get_or_create_company(
        connection=connection,
        name="Test Bank",
        ticker="BANK",
        exchange="TEST",
        currency="EUR",
        fundamental_profile="financial",
    )

    add_period(
        connection,
        company_id,
        date(2024, 12, 31),
        date(2025, 2, 1),
        {
            FinancialMetric.REVENUE: 100.0,
            FinancialMetric.NET_INTEREST_INCOME: 60.0,
            FinancialMetric.NET_INCOME: 10.0,
            FinancialMetric.EPS: 1.0,
            FinancialMetric.SHARES_OUTSTANDING: 100.0,
            FinancialMetric.EQUITY: 80.0,
            FinancialMetric.TANGIBLE_BOOK_VALUE: 70.0,
            FinancialMetric.TOTAL_ASSETS: 1000.0,
            FinancialMetric.NET_LOANS: 600.0,
        },
    )

    add_period(
        connection,
        company_id,
        date(2025, 12, 31),
        date(2026, 2, 1),
        {
            FinancialMetric.REVENUE: 110.0,
            FinancialMetric.NET_INTEREST_INCOME: 66.0,
            FinancialMetric.NET_INCOME: 12.0,
            FinancialMetric.EPS: 1.2,
            FinancialMetric.SHARES_OUTSTANDING: 95.0,
            FinancialMetric.EQUITY: 90.0,
            FinancialMetric.TANGIBLE_BOOK_VALUE: 80.0,
            FinancialMetric.TOTAL_ASSETS: 1100.0,
            FinancialMetric.NET_LOANS: 650.0,
        },
    )

    return connection, company_id


def test_financial_snapshot_is_point_in_time(tmp_path):
    connection, company_id = build_database(tmp_path)

    before = build_financial_fundamental_snapshot(
        connection,
        company_id,
        date(2026, 1, 31),
    )

    after = build_financial_fundamental_snapshot(
        connection,
        company_id,
        date(2026, 2, 1),
    )

    assert before is not None
    assert before.period_end == date(2024, 12, 31)

    assert after is not None
    assert after.period_end == date(2025, 12, 31)
    assert after.net_interest_income == 66.0
    assert after.tangible_book_value == 80.0


def test_financial_growth_uses_previous_known_period(
    tmp_path,
):
    connection, company_id = build_database(tmp_path)

    growth = (
        build_financial_fundamental_growth_snapshot(
            connection,
            company_id,
            date(2026, 2, 1),
        )
    )

    assert growth is not None
    assert growth.current_period_end == date(2025, 12, 31)
    assert growth.previous_period_end == date(2024, 12, 31)

    assert growth.revenue_growth == pytest.approx(0.10)
    assert growth.net_income_growth == pytest.approx(0.20)
    assert growth.eps_growth == pytest.approx(0.20)
    assert growth.shares_growth == pytest.approx(-0.05)

    assert growth.return_on_equity is not None
    assert growth.return_on_equity > 0

    assert growth.return_on_assets is not None
    assert growth.return_on_assets > 0


def test_financial_snapshot_requires_all_metrics(
    tmp_path,
):
    connection, company_id = build_database(tmp_path)

    connection.execute(
        """
        DELETE FROM financials
        WHERE company_id = ?
        AND period_end = ?
        AND metric = ?
        """,
        (
            company_id,
            "2025-12-31",
            FinancialMetric.NET_LOANS.value,
        ),
    )
    connection.commit()

    snapshot = build_financial_fundamental_snapshot(
        connection,
        company_id,
        date(2026, 2, 1),
    )

    assert snapshot is None
