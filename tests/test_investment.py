from datetime import date
from pathlib import Path

from src.assessment import (
    AssessmentLevel,
    RiskLevel,
)
from src.db import connect, managed_connection, initialize_database
from src.investment import (
    AnalysisAvailability,
    build_investment_analysis,
)
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import (
    EstimateRecord,
    FinancialRecord,
    PriceRecord,
)
from src.repository import (
    insert_estimate_record,
    insert_financial_record,
    insert_price_record,
)
from src.scenarios import ValuationScenario


STATEMENT_TYPES = {
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
    FinancialMetric.OPERATING_CASH_FLOW: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.CAPEX: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.FREE_CASH_FLOW: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.CASH: (
        StatementType.BALANCE_SHEET
    ),
    FinancialMetric.TOTAL_DEBT: (
        StatementType.BALANCE_SHEET
    ),
    FinancialMetric.EPS: (
        StatementType.PER_SHARE
    ),
    FinancialMetric.SHARES_OUTSTANDING: (
        StatementType.PER_SHARE
    ),
    FinancialMetric.EQUITY: (
        StatementType.BALANCE_SHEET
    ),
}


SCENARIOS = (
    ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    ),
)


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


def insert_period(
    connection,
    company_id: int,
    period_end: str,
    publication_date: str,
    values: dict[FinancialMetric, float],
) -> None:
    for metric, value in values.items():
        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=STATEMENT_TYPES[
                    metric
                ],
                metric=metric,
                value=value,
                currency="EUR",
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
            ),
        )


def insert_fundamentals(
    connection,
    company_id: int,
) -> None:
    insert_period(
        connection=connection,
        company_id=company_id,
        period_end="2024-12-31",
        publication_date="2025-02-20",
        values={
            FinancialMetric.REVENUE: 1_000.0,
            FinancialMetric.EBITDA: 200.0,
            FinancialMetric.EBIT: 150.0,
            FinancialMetric.NET_INCOME: 100.0,
            FinancialMetric.OPERATING_CASH_FLOW: 180.0,
            FinancialMetric.CAPEX: 50.0,
            FinancialMetric.FREE_CASH_FLOW: 130.0,
            FinancialMetric.CASH: 300.0,
            FinancialMetric.TOTAL_DEBT: 400.0,
            FinancialMetric.EPS: 2.0,
            FinancialMetric.SHARES_OUTSTANDING: 50.0,
            FinancialMetric.EQUITY: 500.0,
        },
    )

    insert_period(
        connection=connection,
        company_id=company_id,
        period_end="2025-12-31",
        publication_date="2026-02-20",
        values={
            FinancialMetric.REVENUE: 1_100.0,
            FinancialMetric.EBITDA: 240.0,
            FinancialMetric.EBIT: 176.0,
            FinancialMetric.NET_INCOME: 120.0,
            FinancialMetric.OPERATING_CASH_FLOW: 210.0,
            FinancialMetric.CAPEX: 50.0,
            FinancialMetric.FREE_CASH_FLOW: 160.0,
            FinancialMetric.CASH: 350.0,
            FinancialMetric.TOTAL_DEBT: 450.0,
            FinancialMetric.EPS: 2.5,
            FinancialMetric.SHARES_OUTSTANDING: 48.0,
            FinancialMetric.EQUITY: 550.0,
        },
    )


def insert_valuation_data(
    connection,
    company_id: int,
) -> None:
    insert_price_record(
        connection,
        PriceRecord(
            company_id=company_id,
            price_date="2026-03-01",
            close=60.0,
            currency="EUR",
        ),
    )

    insert_estimate_record(
        connection,
        EstimateRecord(
            company_id=company_id,
            metric="eps",
            value=3.0,
            currency="EUR",
            fiscal_period_end="2026-12-31",
            estimate_date="2026-02-25",
            analyst_count=12,
        ),
    )


def test_complete_investment_analysis(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_fundamentals(
            connection,
            company_id,
        )
        insert_valuation_data(
            connection,
            company_id,
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.COMPLETE
    )

    assert analysis.valuation is not None
    assert analysis.fundamentals is not None

    assert analysis.valuation.snapshot.price == 60.0
    assert (
        analysis.valuation.snapshot.forward_eps
        == 3.0
    )

    assert (
        analysis.fundamentals.quality_level
        == AssessmentLevel.STRONG
    )
    assert (
        analysis.fundamentals.risk_level
        == RiskLevel.LOW
    )


def test_fundamentals_only_without_estimate(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_fundamentals(
            connection,
            company_id,
        )

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-03-01",
                close=60.0,
                currency="EUR",
            ),
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.FUNDAMENTALS_ONLY
    )

    assert analysis.valuation is None
    assert analysis.fundamentals is not None


def test_valuation_only_without_fundamentals(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_valuation_data(
            connection,
            company_id,
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.VALUATION_ONLY
    )

    assert analysis.valuation is not None
    assert analysis.fundamentals is None


def test_insufficient_without_either_branch(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.INSUFFICIENT
    )

    assert analysis.valuation is None
    assert analysis.fundamentals is None


def test_unpublished_fundamentals_do_not_leak(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_fundamentals(
            connection,
            company_id,
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 2, 19),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.INSUFFICIENT
    )

    assert analysis.fundamentals is None

def test_complete_analysis_contains_value_assessment(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_fundamentals(
            connection,
            company_id,
        )
        insert_valuation_data(
            connection,
            company_id,
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert analysis.value is not None
    assert len(analysis.value.scenarios) == 1

    assert (
        analysis.value.scenarios[0].name
        == "Base"
    )


def test_missing_valuation_means_unknown_value(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_fundamentals(
            connection,
            company_id,
        )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            fiscal_period_end=date(
                2026,
                12,
                31,
            ),
            scenarios=SCENARIOS,
        )

    assert (
        analysis.availability
        == AnalysisAvailability.FUNDAMENTALS_ONLY
    )
    assert analysis.valuation is None
    assert analysis.value is None
    assert analysis.fundamentals is not None