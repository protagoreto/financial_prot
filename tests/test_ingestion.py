from datetime import date
from pathlib import Path

from src.db import connect, initialize_database
from src.ingestion import (
    get_or_create_company,
    ingest_prices,
    ingest_prices_incremental,
    ingest_financials,
)
from src.models import PriceRecord
from src.providers.base import PriceProvider
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.providers.fundamentals_base import FundamentalsProvider


class DummyPriceProvider(PriceProvider):

    @property
    def name(self) -> str:
        return "dummy"

    def get_prices(
        self,
        company_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceRecord]:
        return [
            PriceRecord(
                company_id=company_id,
                price_date=start_date,
                open=10.0,
                high=12.0,
                low=9.0,
                close=11.0,
                adjusted_close=11.0,
                volume=1000,
            )
        ]


def test_get_or_create_company_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        first_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        second_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        rows = connection.execute(
            """
            SELECT *
            FROM companies
            WHERE ticker = 'ITX'
            AND exchange = 'BME'
            """
        ).fetchall()

    assert first_id == second_id
    assert len(rows) == 1


def test_ingest_prices_adds_source_and_currency(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = DummyPriceProvider()

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        count = ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            start_date=date(2026, 9, 18),
            end_date=date(2026, 9, 18),
        )

        price = connection.execute(
            """
            SELECT *
            FROM prices
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()

        source = connection.execute(
            """
            SELECT *
            FROM sources
            WHERE source_id = ?
            """,
            (price["source_id"],),
        ).fetchone()

    assert count == 1
    assert price["currency"] == "EUR"
    assert price["source_id"] is not None
    assert source["provider"] == "dummy"
    assert source["document_type"] == "market_prices"

def test_incremental_ingestion_starts_after_latest_price(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = DummyPriceProvider()

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        first_count = ingest_prices_incremental(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            initial_start_date=date(2026, 9, 17),
            end_date=date(2026, 9, 17),
        )

        second_count = ingest_prices_incremental(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            initial_start_date=date(2026, 9, 17),
            end_date=date(2026, 9, 18),
        )

        dates = [
            row["price_date"]
            for row in connection.execute(
                """
                SELECT price_date
                FROM prices
                ORDER BY price_date
                """
            )
        ]

    assert first_count == 1
    assert second_count == 1

    assert dates == [
        "2026-09-17",
        "2026-09-18",
    ]

def test_incremental_ingestion_backfills_missing_history(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = DummyPriceProvider()

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        # Simulate an incomplete database whose first
        # available price is much later than requested.
        ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            start_date=date(2026, 9, 18),
            end_date=date(2026, 9, 18),
        )

        count = ingest_prices_incremental(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 18),
        )

        dates = [
            row["price_date"]
            for row in connection.execute(
                """
                SELECT price_date
                FROM prices
                ORDER BY price_date
                """
            )
        ]

    assert count == 1

    assert dates == [
        "2026-09-01",
        "2026-09-18",
    ]


def test_incremental_ingestion_tolerates_non_trading_start_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = DummyPriceProvider()

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection,
            name="Inditex",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            start_date=date(2020, 1, 2),
            end_date=date(2020, 1, 2),
        )

        count = ingest_prices_incremental(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            initial_start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
        )

        rows = connection.execute(
            """
            SELECT price_date
            FROM prices
            ORDER BY price_date
            """
        ).fetchall()

    assert count == 0
    assert len(rows) == 1
    assert rows[0]["price_date"] == "2020-01-02"

class DummyFundamentalsProvider(
    FundamentalsProvider
):
    @property
    def name(self) -> str:
        return "dummy"

    def get_annual_financials(
        self,
        company_id: int,
        symbol: str,
    ) -> list[FinancialRecord]:
        return [
            FinancialRecord(
                company_id=company_id,
                statement_type=(
                    StatementType.INCOME_STATEMENT
                ),
                metric=FinancialMetric.REVENUE,
                value=1_000_000.0,
                period_end="2025-12-31",
                period_type=PeriodType.ANNUAL,
            )
        ]

def test_ingest_financials_adds_source_and_currency(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Test Company",
            ticker="TEST",
            exchange="BME",
            currency="EUR",
        )

        count = ingest_financials(
            connection=connection,
            provider=DummyFundamentalsProvider(),
            company_id=company_id,
            symbol="TEST.MC",
            currency="EUR",
        )

        row = connection.execute(
            """
            SELECT
                f.metric,
                f.value,
                f.currency,
                f.publication_date,
                s.provider,
                s.document_type
            FROM financials AS f
            JOIN sources AS s
                ON s.source_id = f.source_id
            WHERE f.company_id = ?
            """,
            (company_id,),
        ).fetchone()

    assert count == 1
    assert row["metric"] == "revenue"
    assert row["value"] == 1_000_000.0
    assert row["currency"] == "EUR"

    # Critical temporal rule:
    # ingestion must not invent publication dates.
    assert row["publication_date"] is None

    assert row["provider"] == "dummy"
    assert row["document_type"] == "annual_financials"