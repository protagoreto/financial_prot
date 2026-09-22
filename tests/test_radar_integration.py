from datetime import date
from pathlib import Path

from src.db import connect, initialize_database
from src.investment import AnalysisAvailability
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
from src.radar_service import run_radar
from src.radar_universe import RadarUniverseIssue
from src.repository import (
    insert_estimate_record,
    insert_financial_record,
    insert_price_record,
)
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


AS_OF_DATE = date(2026, 3, 1)

SCENARIOS = (
    ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    ),
)

STATEMENT_TYPES = {
    FinancialMetric.REVENUE: StatementType.INCOME_STATEMENT,
    FinancialMetric.EBITDA: StatementType.INCOME_STATEMENT,
    FinancialMetric.EBIT: StatementType.INCOME_STATEMENT,
    FinancialMetric.NET_INCOME: StatementType.INCOME_STATEMENT,
    FinancialMetric.OPERATING_CASH_FLOW: StatementType.CASH_FLOW,
    FinancialMetric.CAPEX: StatementType.CASH_FLOW,
    FinancialMetric.FREE_CASH_FLOW: StatementType.CASH_FLOW,
    FinancialMetric.CASH: StatementType.BALANCE_SHEET,
    FinancialMetric.TOTAL_DEBT: StatementType.BALANCE_SHEET,
    FinancialMetric.EPS: StatementType.PER_SHARE,
    FinancialMetric.SHARES_OUTSTANDING: StatementType.PER_SHARE,
    FinancialMetric.EQUITY: StatementType.BALANCE_SHEET,
}


def _insert_company(
    connection,
    company: CompanyConfig,
) -> int:
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
            company.name,
            company.ticker,
            company.exchange,
            company.currency,
        ),
    )
    connection.commit()

    return cursor.lastrowid


def _insert_period(
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
                statement_type=STATEMENT_TYPES[metric],
                metric=metric,
                value=value,
                currency="EUR",
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
            ),
        )


def _insert_fundamentals(
    connection,
    company_id: int,
) -> None:
    _insert_period(
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

    _insert_period(
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


def _insert_valuation_data(
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
            metric=FinancialMetric.EPS,
            value=3.0,
            currency="EUR",
            fiscal_period_end="2026-12-31",
            estimate_date="2026-02-25",
            analyst_count=12,
        ),
    )


def test_run_radar_end_to_end_preserves_resolved_and_unresolved(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    resolved = CompanyConfig(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
        exchange="BME",
        currency="EUR",
    )
    missing = CompanyConfig(
        name="Missing Company",
        ticker="MISS",
        symbol="MISS.MC",
        exchange="BME",
        currency="EUR",
    )

    with connect(db_path) as connection:
        company_id = _insert_company(
            connection,
            resolved,
        )

        _insert_fundamentals(
            connection,
            company_id,
        )
        _insert_valuation_data(
            connection,
            company_id,
        )

        result = run_radar(
            connection=connection,
            universe=(resolved, missing),
            as_of_date=AS_OF_DATE,
            scenarios=SCENARIOS,
        )

    assert len(result.snapshot.entries) == 1

    entry = result.snapshot.entries[0]

    assert entry.company_id == company_id
    assert entry.name == "Test Company"
    assert entry.ticker == "TEST"
    assert entry.exchange == "BME"
    assert entry.as_of_date == AS_OF_DATE
    assert entry.fiscal_period_end == date(2026, 12, 31)
    assert entry.availability == AnalysisAvailability.COMPLETE

    assert len(entry.scenarios) == 1
    assert entry.scenarios[0].name == "Base"
    assert entry.scenarios[0].expected_return is not None
    assert entry.scenarios[0].required_price is not None
    assert entry.scenarios[0].price_margin is not None

    assert len(result.unresolved) == 1
    assert result.unresolved[0].company == missing
    assert (
        result.unresolved[0].issue
        == RadarUniverseIssue.COMPANY_NOT_FOUND
    )
