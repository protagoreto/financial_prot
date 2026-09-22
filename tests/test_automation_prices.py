from datetime import date
from pathlib import Path

from src.automation import update_prices
from src.db import connect, initialize_database
from src.models import PriceRecord
from src.providers.base import PriceProvider
from src.universe import CompanyConfig


class RecordingPriceProvider(PriceProvider):
    def __init__(self) -> None:
        self.calls: list[
            tuple[int, str, date, date]
        ] = []

    @property
    def name(self) -> str:
        return "recording"

    def get_prices(
        self,
        company_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceRecord]:
        self.calls.append(
            (
                company_id,
                symbol,
                start_date,
                end_date,
            )
        )

        return [
            PriceRecord(
                company_id=company_id,
                price_date=start_date,
                open=10.0,
                high=12.0,
                low=9.0,
                close=11.0,
                adjusted_close=11.0,
                volume=1_000.0,
            )
        ]


def _company(
    name: str,
    ticker: str,
    symbol: str,
) -> CompanyConfig:
    return CompanyConfig(
        name=name,
        ticker=ticker,
        symbol=symbol,
        exchange="BME",
        currency="EUR",
    )


def test_update_prices_processes_universe_in_order(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = RecordingPriceProvider()

    first = _company(
        name="First Company",
        ticker="FIRST",
        symbol="FIRST.MC",
    )
    second = _company(
        name="Second Company",
        ticker="SECOND",
        symbol="SECOND.MC",
    )

    with connect(db_path) as connection:
        result = update_prices(
            connection=connection,
            provider=provider,
            universe=(first, second),
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 2),
        )

    assert result.start_date == date(2026, 9, 1)
    assert result.end_date == date(2026, 9, 2)

    assert tuple(
        update.company
        for update in result.companies
    ) == (first, second)

    assert tuple(
        update.processed_records
        for update in result.companies
    ) == (1, 1)

    assert result.processed_records == 2

    assert tuple(
        call[1]
        for call in provider.calls
    ) == (
        "FIRST.MC",
        "SECOND.MC",
    )


def test_update_prices_creates_companies_and_prices(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = RecordingPriceProvider()

    company = _company(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
    )

    with connect(db_path) as connection:
        result = update_prices(
            connection=connection,
            provider=provider,
            universe=(company,),
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 1),
        )

        company_row = connection.execute(
            """
            SELECT
                company_id,
                ticker,
                exchange
            FROM companies
            """
        ).fetchone()

        price_row = connection.execute(
            """
            SELECT
                company_id,
                price_date,
                close,
                currency
            FROM prices
            """
        ).fetchone()

    assert len(result.companies) == 1
    assert (
        result.companies[0].company_id
        == company_row["company_id"]
    )

    assert company_row["ticker"] == "TEST"
    assert company_row["exchange"] == "BME"

    assert (
        price_row["company_id"]
        == company_row["company_id"]
    )
    assert price_row["price_date"] == "2026-09-01"
    assert price_row["close"] == 11.0
    assert price_row["currency"] == "EUR"


def test_update_prices_reuses_existing_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = RecordingPriceProvider()

    company = _company(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
    )

    with connect(db_path) as connection:
        first = update_prices(
            connection=connection,
            provider=provider,
            universe=(company,),
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 1),
        )

        second = update_prices(
            connection=connection,
            provider=provider,
            universe=(company,),
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 2),
        )

        company_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM companies
            """
        ).fetchone()["count"]

        price_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM prices
            """
        ).fetchone()["count"]

    assert (
        first.companies[0].company_id
        == second.companies[0].company_id
    )
    assert company_count == 1
    assert price_count == 2
    assert second.processed_records == 1


def test_update_prices_accepts_empty_universe(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = RecordingPriceProvider()

    with connect(db_path) as connection:
        result = update_prices(
            connection=connection,
            provider=provider,
            universe=(),
            initial_start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 2),
        )

    assert result.companies == ()
    assert result.processed_records == 0
    assert provider.calls == []


def test_update_prices_rejects_inverted_date_range(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    provider = RecordingPriceProvider()

    company = _company(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
    )

    with connect(db_path) as connection:
        try:
            update_prices(
                connection=connection,
                provider=provider,
                universe=(company,),
                initial_start_date=date(2026, 9, 2),
                end_date=date(2026, 9, 1),
            )
        except ValueError as exc:
            assert str(exc) == (
                "Initial start date cannot be after end date."
            )
        else:
            raise AssertionError(
                "Expected ValueError."
            )

    assert provider.calls == []
