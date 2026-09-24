from datetime import date

from src.assessment import (
    AssessmentLevel,
    RiskLevel,
)
from src.db import connect, initialize_database
from src.financial_assessment import (
    assess_financial_fundamentals,
)
from src.financial_signals import (
    build_financial_fundamental_signals,
)
from src.ingestion import get_or_create_company
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.repository import insert_financial_record


METRICS = (
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


def insert_period(
    connection,
    company_id,
    period_end,
    publication_date,
    values,
):
    for metric, statement_type in METRICS:
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


def test_financial_signals_and_assessment(tmp_path):
    db_path = tmp_path / "financial.sqlite"
    initialize_database(db_path)

    connection = connect(db_path)

    company_id = get_or_create_company(
        connection=connection,
        name="Test Bank",
        ticker="BANK",
        exchange="TEST",
        currency="EUR",
        fundamental_profile="financial",
    )

    insert_period(
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

    insert_period(
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

    signals = build_financial_fundamental_signals(
        connection=connection,
        company_id=company_id,
        as_of_date=date(2026, 2, 1),
    )

    assert signals is not None

    assert signals.positive_net_income is True
    assert signals.positive_roe is True
    assert signals.positive_roa is True
    assert (
        signals.positive_tangible_book_growth
        is True
    )

    assert signals.revenue_decline is False
    assert (
        signals.net_interest_income_decline
        is False
    )
    assert signals.eps_decline is False
    assert signals.tangible_book_decline is False
    assert signals.share_dilution is False

    assessment = assess_financial_fundamentals(
        signals
    )

    assert assessment is not None
    assert (
        assessment.quality_level
        == AssessmentLevel.STRONG
    )
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.value_trap_warning is False
    assert assessment.known_quality_signals == 4
    assert assessment.positive_quality_signals == 4
    assert assessment.known_risk_signals == 5
    assert assessment.active_risk_signals == 0
