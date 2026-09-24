from datetime import date

import pandas as pd
import pytest

from src.db import connect, managed_connection, initialize_database
from src.ingestion import ingest_dividends
from src.models import DividendRecord
from src.providers.yahoo_dividends import (
    YahooDividendProvider,
)
from src.repository import insert_dividend_record


class FakeTicker:
    def __init__(self, dividends):
        self.dividends = dividends


def _dividends():
    return pd.Series(
        [0.84, 0.84, 0.875],
        index=pd.to_datetime(
            [
                "2025-04-29T07:00:00Z",
                "2025-10-30T08:00:00Z",
                "2026-04-29T07:00:00Z",
            ],
            utc=True,
        ),
        name="Dividends",
    )


def _insert_company(connection):
    connection.execute(
        """
        INSERT INTO companies (
            company_id,
            name,
            ticker,
            exchange,
            currency
        )
        VALUES (
            1,
            'Test Company',
            'TST',
            'BME',
            'EUR'
        )
        """
    )
    connection.commit()


def test_dividend_record_requires_positive_amount():
    with pytest.raises(ValueError):
        DividendRecord(
            company_id=1,
            ex_date=date(2026, 4, 29),
            amount=0,
            currency="EUR",
        )


def test_yahoo_dividends_are_normalized(
    monkeypatch,
):
    fake = FakeTicker(_dividends())

    monkeypatch.setattr(
        "src.providers.yahoo_dividends.yf.Ticker",
        lambda symbol: fake,
    )

    records = YahooDividendProvider().get_dividends(
        company_id=1,
        symbol="ITX.MC",
        currency="EUR",
    )

    assert len(records) == 3
    assert records[0].company_id == 1
    assert records[0].ex_date == date(2025, 4, 29)
    assert records[0].amount == pytest.approx(0.84)
    assert records[0].currency == "EUR"
    assert records[0].payment_date is None
    assert records[0].dividend_type is None
    assert records[0].source_id is None

    assert records[-1].ex_date == date(2026, 4, 29)
    assert records[-1].amount == pytest.approx(0.875)


def test_yahoo_dividends_empty_series(
    monkeypatch,
):
    fake = FakeTicker(
        pd.Series(dtype=float)
    )

    monkeypatch.setattr(
        "src.providers.yahoo_dividends.yf.Ticker",
        lambda symbol: fake,
    )

    records = YahooDividendProvider().get_dividends(
        company_id=1,
        symbol="ITX.MC",
        currency="EUR",
    )

    assert records == []


def test_insert_dividend_record_is_idempotent(
    tmp_path,
):
    db_path = tmp_path / "dividends.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        _insert_company(connection)

        record = DividendRecord(
            company_id=1,
            ex_date=date(2026, 4, 29),
            amount=0.875,
            currency="EUR",
        )

        first_id = insert_dividend_record(
            connection,
            record,
        )
        second_id = insert_dividend_record(
            connection,
            record,
        )

        count = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM dividends
            """
        ).fetchone()["n"]

    assert second_id == first_id
    assert count == 1


def test_dividend_ingestion_is_idempotent(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "dividends.sqlite"
    initialize_database(db_path)

    fake = FakeTicker(_dividends())

    monkeypatch.setattr(
        "src.providers.yahoo_dividends.yf.Ticker",
        lambda symbol: fake,
    )

    provider = YahooDividendProvider()

    with managed_connection(db_path) as connection:
        _insert_company(connection)

        first = ingest_dividends(
            connection=connection,
            provider=provider,
            company_id=1,
            symbol="TST.MC",
            currency="EUR",
        )

        source_count_after_first = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM sources
            WHERE provider = 'yahoo'
            AND document_type = 'dividend_history'
            """
        ).fetchone()["n"]

        second = ingest_dividends(
            connection=connection,
            provider=provider,
            company_id=1,
            symbol="TST.MC",
            currency="EUR",
        )

        source_count_after_second = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM sources
            WHERE provider = 'yahoo'
            AND document_type = 'dividend_history'
            """
        ).fetchone()["n"]

        rows = connection.execute(
            """
            SELECT
                d.*,
                s.provider,
                s.document_type,
                s.confidence
            FROM dividends AS d
            JOIN sources AS s
                ON s.source_id = d.source_id
            ORDER BY d.ex_date
            """
        ).fetchall()

    assert first == 3
    assert second == 0
    assert len(rows) == 3

    assert source_count_after_first == 1
    assert source_count_after_second == 1

    assert rows[0]["provider"] == "yahoo"
    assert (
        rows[0]["document_type"]
        == "dividend_history"
    )
    assert rows[0]["confidence"] == "secondary"
