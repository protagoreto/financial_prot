from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.fundamentals import build_fundamental_snapshot
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.repository import insert_financial_record


def create_company(connection) -> int:
    cursor = connection.execute(
        """
        INSERT INTO companies (
            name,
            ticker,
            exchange,
            currency
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "Test Company",
            "TEST",
            "BME",
            "EUR",
        ),
    )

    connection.commit()
    return cursor.lastrowid


def insert_annual_financial(
    connection,
    company_id: int,
    metric: FinancialMetric,
    value: float,
    statement_type: StatementType,
) -> None:
    insert_financial_record(
        connection,
        FinancialRecord(
            company_id=company_id,
            statement_type=statement_type,
            metric=metric,
            value=value,
            currency="EUR",
            period_end="2025-12-31",
            period_type=PeriodType.ANNUAL,
            publication_date="2026-02-26",
        ),
    )


def test_build_fundamental_snapshot(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        records = [
            (
                FinancialMetric.REVENUE,
                1_000.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBITDA,
                200.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBIT,
                150.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.NET_INCOME,
                100.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.OPERATING_CASH_FLOW,
                180.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CAPEX,
                50.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.FREE_CASH_FLOW,
                130.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CASH,
                300.0,
                StatementType.BALANCE_SHEET,
            ),
            (
                FinancialMetric.TOTAL_DEBT,
                500.0,
                StatementType.BALANCE_SHEET,
            ),
        ]

        for metric, value, statement_type in records:
            insert_annual_financial(
                connection=connection,
                company_id=company_id,
                metric=metric,
                value=value,
                statement_type=statement_type,
            )

        snapshot = build_fundamental_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert snapshot is not None

    assert snapshot.period_end == date(
        2025,
        12,
        31,
    )
    assert snapshot.publication_date == date(
        2026,
        2,
        26,
    )

    assert snapshot.revenue == 1_000.0
    assert snapshot.ebitda == 200.0
    assert snapshot.ebit == 150.0
    assert snapshot.net_income == 100.0

    assert snapshot.ebitda_margin == pytest.approx(
        0.20
    )
    assert snapshot.ebit_margin == pytest.approx(
        0.15
    )
    assert snapshot.net_margin == pytest.approx(
        0.10
    )
    assert snapshot.fcf_margin == pytest.approx(
        0.13
    )

    assert snapshot.net_debt == pytest.approx(
        200.0
    )
    assert (
        snapshot.net_debt_to_ebitda
        == pytest.approx(1.0)
    )

def test_fundamental_snapshot_rejects_mixed_periods(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        metrics = [
            (
                FinancialMetric.REVENUE,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBITDA,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBIT,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.NET_INCOME,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.OPERATING_CASH_FLOW,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CAPEX,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.FREE_CASH_FLOW,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CASH,
                StatementType.BALANCE_SHEET,
            ),
            (
                FinancialMetric.TOTAL_DEBT,
                StatementType.BALANCE_SHEET,
            ),
        ]

        for metric, statement_type in metrics:
            insert_financial_record(
                connection,
                FinancialRecord(
                    company_id=company_id,
                    statement_type=statement_type,
                    metric=metric,
                    value=100.0,
                    currency="EUR",
                    period_end="2024-12-31",
                    period_type=PeriodType.ANNUAL,
                    publication_date="2025-02-20",
                ),
            )

        for metric, statement_type in metrics:
            if metric == FinancialMetric.TOTAL_DEBT:
                continue

            insert_financial_record(
                connection,
                FinancialRecord(
                    company_id=company_id,
                    statement_type=statement_type,
                    metric=metric,
                    value=200.0,
                    currency="EUR",
                    period_end="2025-12-31",
                    period_type=PeriodType.ANNUAL,
                    publication_date="2026-02-20",
                ),
            )

        snapshot = build_fundamental_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert snapshot is None

def test_fundamental_snapshot_rejects_unpublished_period(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        records = [
            (
                FinancialMetric.REVENUE,
                1_000.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBITDA,
                200.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.EBIT,
                150.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.NET_INCOME,
                100.0,
                StatementType.INCOME_STATEMENT,
            ),
            (
                FinancialMetric.OPERATING_CASH_FLOW,
                180.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CAPEX,
                50.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.FREE_CASH_FLOW,
                130.0,
                StatementType.CASH_FLOW,
            ),
            (
                FinancialMetric.CASH,
                300.0,
                StatementType.BALANCE_SHEET,
            ),
            (
                FinancialMetric.TOTAL_DEBT,
                500.0,
                StatementType.BALANCE_SHEET,
            ),
        ]

        for metric, value, statement_type in records:
            insert_annual_financial(
                connection=connection,
                company_id=company_id,
                metric=metric,
                value=value,
                statement_type=statement_type,
            )

        snapshot = build_fundamental_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 2, 25),
        )

    assert snapshot is None