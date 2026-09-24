from datetime import date
from pathlib import Path

import pytest

from src.db import connect, managed_connection, initialize_database
from src.fundamentals import (
    build_fundamental_growth_snapshot,
    build_fundamental_snapshot,
)
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

    with managed_connection(db_path) as connection:
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

    with managed_connection(db_path) as connection:
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

    with managed_connection(db_path) as connection:
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

def insert_growth_period(
    connection,
    company_id: int,
    period_end: str,
    publication_date: str,
    values: dict[FinancialMetric, float],
) -> None:
    statement_types = {
        FinancialMetric.REVENUE: (
            StatementType.INCOME_STATEMENT
        ),
        FinancialMetric.EBITDA: (
            StatementType.INCOME_STATEMENT
        ),
        FinancialMetric.EBIT: (
            StatementType.INCOME_STATEMENT
        ),
        FinancialMetric.NET_INCOME: (
            StatementType.INCOME_STATEMENT
        ),
        FinancialMetric.EPS: StatementType.PER_SHARE,
        FinancialMetric.FREE_CASH_FLOW: (
            StatementType.CASH_FLOW
        ),
        FinancialMetric.SHARES_OUTSTANDING: (
            StatementType.PER_SHARE
        ),
        FinancialMetric.EQUITY: (
            StatementType.BALANCE_SHEET
        ),
    }

    for metric, value in values.items():
        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=statement_types[metric],
                metric=metric,
                value=value,
                currency="EUR",
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
            ),
        )


def test_build_fundamental_growth_snapshot(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2024-12-31",
            publication_date="2025-02-20",
            values={
                FinancialMetric.REVENUE: 1_000.0,
                FinancialMetric.EBITDA: 200.0,
                FinancialMetric.EBIT: 150.0,
                FinancialMetric.NET_INCOME: 100.0,
                FinancialMetric.EPS: 2.0,
                FinancialMetric.FREE_CASH_FLOW: 120.0,
                FinancialMetric.SHARES_OUTSTANDING: 50.0,
                FinancialMetric.EQUITY: 500.0,
            },
        )

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2025-12-31",
            publication_date="2026-02-20",
            values={
                FinancialMetric.REVENUE: 1_100.0,
                FinancialMetric.EBITDA: 230.0,
                FinancialMetric.EBIT: 165.0,
                FinancialMetric.NET_INCOME: 120.0,
                FinancialMetric.EPS: 2.5,
                FinancialMetric.FREE_CASH_FLOW: 150.0,
                FinancialMetric.SHARES_OUTSTANDING: 48.0,
                FinancialMetric.EQUITY: 550.0,
            },
        )

        snapshot = build_fundamental_growth_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert snapshot is not None

    assert snapshot.current_period_end == date(
        2025,
        12,
        31,
    )
    assert snapshot.previous_period_end == date(
        2024,
        12,
        31,
    )

    assert snapshot.revenue_growth == pytest.approx(
        0.10
    )
    assert snapshot.ebitda_growth == pytest.approx(
        0.15
    )
    assert snapshot.ebit_growth == pytest.approx(
        0.10
    )
    assert snapshot.net_income_growth == pytest.approx(
        0.20
    )
    assert snapshot.eps_growth == pytest.approx(
        0.25
    )
    assert snapshot.free_cash_flow_growth == pytest.approx(
        0.25
    )
    assert snapshot.shares_growth == pytest.approx(
        -0.04
    )

    assert snapshot.return_on_equity == pytest.approx(
        120.0 / 525.0
    )
    assert snapshot.is_annual_comparison is True
    assert snapshot.years_between_periods == pytest.approx(
        1.0,
        abs=0.01,
    )

    assert snapshot.revenue_cagr == pytest.approx(
        0.10,
        abs=0.001,
    )
    assert snapshot.eps_cagr == pytest.approx(
        0.25,
        abs=0.001,
    )


def test_growth_snapshot_respects_point_in_time(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        previous_values = {
            FinancialMetric.REVENUE: 1_000.0,
            FinancialMetric.EBITDA: 200.0,
            FinancialMetric.EBIT: 150.0,
            FinancialMetric.NET_INCOME: 100.0,
            FinancialMetric.EPS: 2.0,
            FinancialMetric.FREE_CASH_FLOW: 120.0,
            FinancialMetric.SHARES_OUTSTANDING: 50.0,
            FinancialMetric.EQUITY: 500.0,
        }

        current_values = {
            FinancialMetric.REVENUE: 1_100.0,
            FinancialMetric.EBITDA: 230.0,
            FinancialMetric.EBIT: 165.0,
            FinancialMetric.NET_INCOME: 120.0,
            FinancialMetric.EPS: 2.5,
            FinancialMetric.FREE_CASH_FLOW: 150.0,
            FinancialMetric.SHARES_OUTSTANDING: 48.0,
            FinancialMetric.EQUITY: 550.0,
        }

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2024-12-31",
            publication_date="2025-02-20",
            values=previous_values,
        )

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2025-12-31",
            publication_date="2026-03-11",
            values=current_values,
        )

        before = build_fundamental_growth_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 10),
        )

        on_publication = (
            build_fundamental_growth_snapshot(
                connection=connection,
                company_id=company_id,
                as_of_date=date(2026, 3, 11),
            )
        )

    assert before is None
    assert on_publication is not None
    assert on_publication.current_period_end == date(
        2025,
        12,
        31,
    )


def test_growth_snapshot_rejects_incomplete_current_period(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        previous_values = {
            FinancialMetric.REVENUE: 1_000.0,
            FinancialMetric.EBITDA: 200.0,
            FinancialMetric.EBIT: 150.0,
            FinancialMetric.NET_INCOME: 100.0,
            FinancialMetric.EPS: 2.0,
            FinancialMetric.FREE_CASH_FLOW: 120.0,
            FinancialMetric.SHARES_OUTSTANDING: 50.0,
            FinancialMetric.EQUITY: 500.0,
        }

        current_values = {
            FinancialMetric.REVENUE: 1_100.0,
            FinancialMetric.EBITDA: 230.0,
            FinancialMetric.EBIT: 165.0,
            FinancialMetric.NET_INCOME: 120.0,
            FinancialMetric.EPS: 2.5,
            FinancialMetric.FREE_CASH_FLOW: 150.0,
            FinancialMetric.SHARES_OUTSTANDING: 48.0,
        }

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2024-12-31",
            publication_date="2025-02-20",
            values=previous_values,
        )

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2025-12-31",
            publication_date="2026-02-20",
            values=current_values,
        )

        snapshot = build_fundamental_growth_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert snapshot is None


def test_growth_snapshot_skips_incomplete_previous_period(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        complete_2023 = {
            FinancialMetric.REVENUE: 900.0,
            FinancialMetric.EBITDA: 180.0,
            FinancialMetric.EBIT: 130.0,
            FinancialMetric.NET_INCOME: 90.0,
            FinancialMetric.EPS: 1.8,
            FinancialMetric.FREE_CASH_FLOW: 100.0,
            FinancialMetric.SHARES_OUTSTANDING: 51.0,
            FinancialMetric.EQUITY: 450.0,
        }

        incomplete_2024 = {
            FinancialMetric.REVENUE: 1_000.0,
        }

        complete_2025 = {
            FinancialMetric.REVENUE: 1_100.0,
            FinancialMetric.EBITDA: 230.0,
            FinancialMetric.EBIT: 165.0,
            FinancialMetric.NET_INCOME: 120.0,
            FinancialMetric.EPS: 2.5,
            FinancialMetric.FREE_CASH_FLOW: 150.0,
            FinancialMetric.SHARES_OUTSTANDING: 48.0,
            FinancialMetric.EQUITY: 550.0,
        }

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2023-12-31",
            publication_date="2024-02-20",
            values=complete_2023,
        )

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2024-12-31",
            publication_date="2025-02-20",
            values=incomplete_2024,
        )

        insert_growth_period(
            connection=connection,
            company_id=company_id,
            period_end="2025-12-31",
            publication_date="2026-02-20",
            values=complete_2025,
        )

        snapshot = build_fundamental_growth_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert snapshot is not None
    assert snapshot.previous_period_end == date(
        2023,
        12,
        31,
    )
        
    assert snapshot.is_annual_comparison is False

    assert snapshot.years_between_periods == pytest.approx(
        2.0,
        abs=0.01,
    )

    assert snapshot.revenue_growth == pytest.approx(
        1_100.0 / 900.0 - 1
    )

    assert snapshot.revenue_cagr == pytest.approx(
        (1_100.0 / 900.0) ** 0.5 - 1,
        abs=0.001,
    )
    
