from datetime import date

from src.coverage import build_company_coverage
from src.db import connect, initialize_database
from src.ingestion import get_or_create_company
from src.investment import AnalysisAvailability
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.repository import insert_financial_record


FINANCIAL_METRICS = (
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


def _insert_period(
    connection,
    company_id,
    period_end,
    publication_date,
    values,
):
    for metric, statement_type in FINANCIAL_METRICS:
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


def _build_financial_company(tmp_path):
    db_path = tmp_path / "profile.sqlite"
    initialize_database(db_path)

    connection = connect(db_path)

    company_id = get_or_create_company(
        connection=connection,
        name="Profile Bank",
        ticker="BANK",
        exchange="TEST",
        currency="EUR",
        fundamental_profile="financial",
    )

    _insert_period(
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

    _insert_period(
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


def test_financial_coverage_uses_financial_contract(
    tmp_path,
):
    connection, company_id = (
        _build_financial_company(tmp_path)
    )

    coverage = build_company_coverage(
        connection=connection,
        company_id=company_id,
        as_of_date=date(2026, 2, 1),
    )

    assert coverage.fundamental_snapshot_available is True
    assert coverage.fundamental_growth_available is True
    assert coverage.fundamentals_available is True

    assert coverage.missing_snapshot_metrics == ()
    assert coverage.missing_growth_metrics == ()

    assert (
        coverage.availability
        == AnalysisAvailability.FUNDAMENTALS_ONLY
    )


def test_financial_coverage_is_point_in_time(
    tmp_path,
):
    connection, company_id = (
        _build_financial_company(tmp_path)
    )

    coverage = build_company_coverage(
        connection=connection,
        company_id=company_id,
        as_of_date=date(2025, 1, 31),
    )

    assert coverage.fundamental_snapshot_available is False
    assert coverage.fundamental_growth_available is False
    assert coverage.fundamentals_available is False

    assert (
        FinancialMetric.NET_INTEREST_INCOME
        in coverage.missing_snapshot_metrics
    )
    assert (
        FinancialMetric.TANGIBLE_BOOK_VALUE
        in coverage.missing_growth_metrics
    )


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.profile = None

    def get_annual_financials(
        self,
        company_id,
        symbol,
        fundamental_profile="operating",
    ):
        self.profile = fundamental_profile
        return []


def test_ingestion_propagates_financial_profile(
    tmp_path,
):
    from src.ingestion import ingest_financials

    db_path = tmp_path / "ingestion.sqlite"
    initialize_database(db_path)

    connection = connect(db_path)

    provider = FakeProvider()

    processed = ingest_financials(
        connection=connection,
        provider=provider,
        company_id=1,
        symbol="BANK.TEST",
        currency="EUR",
        fundamental_profile="financial",
    )

    assert processed == 0
    assert provider.profile == "financial"
