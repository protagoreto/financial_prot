from datetime import date
from pathlib import Path

from src.db import connect, initialize_database
from src.ingestion import (
    get_or_create_company,
    ingest_prices,
    ingest_prices_incremental,
)
from src.models import PriceRecord
from src.providers.base import PriceProvider


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