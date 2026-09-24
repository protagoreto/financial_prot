from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.ingestion import get_or_create_company
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import (
    DividendRecord,
    EstimateRecord,
    FinancialRecord,
    PriceRecord,
)
from src.onboarding import (
    OnboardingStatus,
    onboard_company,
)
from src.providers.publication_dates_base import (
    PublicationDateRecord,
)


class DummyPriceProvider:
    name = "dummy_prices"

    def get_prices(
        self,
        company_id,
        symbol,
        start_date,
        end_date,
    ):
        return [
            PriceRecord(
                company_id=company_id,
                price_date=start_date,
                close=100.0,
            )
        ]


class DummyFundamentalsProvider:
    name = "dummy_fundamentals"

    def get_annual_financials(
        self,
        company_id,
        symbol,
        fundamental_profile="operating",
    ):
        metric = (
            FinancialMetric.NET_INTEREST_INCOME
            if fundamental_profile == "financial"
            else FinancialMetric.REVENUE
        )

        return [
            FinancialRecord(
                company_id=company_id,
                statement_type=(
                    StatementType.INCOME_STATEMENT
                ),
                metric=metric,
                value=1_000.0,
                period_end=date(2025, 12, 31),
                period_type=PeriodType.ANNUAL,
            )
        ]


class DummyEstimateProvider:
    name = "dummy_estimates"

    def get_forward_eps_estimate(
        self,
        company_id,
        symbol,
        estimate_date=None,
    ):
        observation_date = (
            estimate_date or date(2026, 9, 24)
        )

        return EstimateRecord(
            company_id=company_id,
            metric=FinancialMetric.EPS,
            value=5.0,
            fiscal_period_end=date(2027, 12, 31),
            estimate_date=observation_date,
            analyst_count=10,
        )


class DummyPublicationDateProvider:
    name = "dummy_publication_dates"

    def get_publication_dates(
        self,
        company_id,
        symbol,
    ):
        return [
            PublicationDateRecord(
                company_id=company_id,
                period_end=date(2025, 12, 31),
                period_type=PeriodType.ANNUAL,
                publication_date=date(2026, 2, 15),
                source_url=(
                    "https://example.test/filing"
                ),
            )
        ]


class DummyDividendProvider:
    name = "dummy_dividends"

    def get_dividends(
        self,
        company_id,
        symbol,
        currency,
    ):
        return [
            DividendRecord(
                company_id=company_id,
                ex_date=date(2026, 6, 1),
                amount=1.0,
                currency=currency,
            )
        ]


def _company(
    connection,
    *,
    symbol="TEST.MC",
    profile="operating",
):
    return get_or_create_company(
        connection=connection,
        name="Test Company",
        ticker="TEST",
        exchange="TEST",
        currency="EUR",
        fundamental_profile=profile,
        symbol=symbol,
    )


def test_onboard_company_runs_all_steps(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=(
                DummyFundamentalsProvider()
            ),
            estimate_provider=DummyEstimateProvider(),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
            estimate_date=date(2026, 9, 24),
            publication_date_provider=(
                DummyPublicationDateProvider()
            ),
        )

        financial = connection.execute(
            """
            SELECT publication_date
            FROM financials
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()

        publication = connection.execute(
            """
            SELECT period_end, period_type, publication_date
            FROM publication_dates
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()

    assert result.company_id == company_id
    assert result.symbol == "TEST.MC"
    assert result.succeeded == 5
    assert result.unavailable == 0
    assert result.failed == 0

    assert [step.name for step in result.steps] == [
        "prices",
        "financials",
        "forward_eps",
        "dividends",
        "publication_dates",
    ]

    assert all(
        step.status == OnboardingStatus.SUCCESS
        for step in result.steps
    )

    # Financial rows remain raw; PIT availability comes from
    # the separately verified publication_dates table.
    assert financial["publication_date"] is None
    assert publication["period_end"] == "2025-12-31"
    assert publication["period_type"] == "annual"
    assert publication["publication_date"] == "2026-02-15"


def test_onboard_company_uses_financial_profile(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(
            connection,
            profile="financial",
        )

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=(
                DummyFundamentalsProvider()
            ),
            estimate_provider=DummyEstimateProvider(),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
        )

        row = connection.execute(
            """
            SELECT metric
            FROM financials
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()

    assert result.failed == 0
    assert row["metric"] == "net_interest_income"


def test_onboard_company_continues_after_unavailable_step(
    tmp_path: Path,
):
    class UnavailableEstimateProvider:
        name = "unavailable_estimates"

        def get_forward_eps_estimate(
            self,
            company_id,
            symbol,
            estimate_date=None,
        ):
            raise ValueError(
                "Forward EPS estimate unavailable"
            )

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=(
                DummyFundamentalsProvider()
            ),
            estimate_provider=(
                UnavailableEstimateProvider()
            ),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
        )

    statuses = {
        step.name: step.status
        for step in result.steps
    }

    assert statuses["prices"] == OnboardingStatus.SUCCESS
    assert statuses["financials"] == OnboardingStatus.SUCCESS
    assert statuses["forward_eps"] == (
        OnboardingStatus.UNAVAILABLE
    )
    assert statuses["dividends"] == OnboardingStatus.SUCCESS

    assert result.succeeded == 3
    assert result.unavailable == 2
    assert result.failed == 0


def test_onboard_company_continues_after_failed_step(
    tmp_path: Path,
):
    class BrokenFundamentalsProvider:
        name = "broken_fundamentals"

        def get_annual_financials(
            self,
            company_id,
            symbol,
            fundamental_profile="operating",
        ):
            raise RuntimeError("provider failure")

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=(
                BrokenFundamentalsProvider()
            ),
            estimate_provider=DummyEstimateProvider(),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
        )

    statuses = {
        step.name: step.status
        for step in result.steps
    }

    assert statuses["financials"] == OnboardingStatus.FAILED
    assert statuses["forward_eps"] == OnboardingStatus.SUCCESS
    assert statuses["dividends"] == OnboardingStatus.SUCCESS

    assert result.succeeded == 3
    assert result.unavailable == 1
    assert result.failed == 1


def test_onboard_company_requires_persisted_symbol(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(
            connection,
            symbol=None,
        )

        with pytest.raises(
            ValueError,
            match="provider symbol",
        ):
            onboard_company(
                connection=connection,
                company_id=company_id,
                price_provider=DummyPriceProvider(),
                fundamentals_provider=(
                    DummyFundamentalsProvider()
                ),
                estimate_provider=(
                    DummyEstimateProvider()
                ),
                dividend_provider=(
                    DummyDividendProvider()
                ),
                initial_price_date=date(2026, 9, 1),
                end_date=date(2026, 9, 24),
            )


def test_onboard_company_rejects_invalid_date_range(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        with pytest.raises(
            ValueError,
            match="initial_price_date",
        ):
            onboard_company(
                connection=connection,
                company_id=company_id,
                price_provider=DummyPriceProvider(),
                fundamentals_provider=(
                    DummyFundamentalsProvider()
                ),
                estimate_provider=(
                    DummyEstimateProvider()
                ),
                dividend_provider=(
                    DummyDividendProvider()
                ),
                initial_price_date=date(2026, 9, 25),
                end_date=date(2026, 9, 24),
            )


def test_onboard_company_marks_publication_dates_unavailable_without_provider(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=DummyFundamentalsProvider(),
            estimate_provider=DummyEstimateProvider(),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
        )

    publication_step = next(
        step
        for step in result.steps
        if step.name == "publication_dates"
    )

    assert publication_step.status == OnboardingStatus.UNAVAILABLE
    assert publication_step.processed is None
    assert publication_step.detail == (
        "Publication date provider not configured"
    )


def test_onboard_company_continues_after_unavailable_publication_dates(
    tmp_path: Path,
):
    class UnavailablePublicationDateProvider:
        name = "unavailable_publication_dates"

        def get_publication_dates(
            self,
            company_id,
            symbol,
        ):
            raise ValueError("SEC CIK unavailable")

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _company(connection)

        result = onboard_company(
            connection=connection,
            company_id=company_id,
            price_provider=DummyPriceProvider(),
            fundamentals_provider=DummyFundamentalsProvider(),
            estimate_provider=DummyEstimateProvider(),
            dividend_provider=DummyDividendProvider(),
            initial_price_date=date(2026, 9, 1),
            end_date=date(2026, 9, 24),
            publication_date_provider=(
                UnavailablePublicationDateProvider()
            ),
        )

    statuses = {
        step.name: step.status
        for step in result.steps
    }

    assert statuses["publication_dates"] == (
        OnboardingStatus.UNAVAILABLE
    )
    assert result.failed == 0
