from datetime import date

import pandas as pd
import pytest

from src.db import connect, managed_connection, initialize_database
from src.ingestion import ingest_forward_eps_estimate
from src.metrics import FinancialMetric
from src.providers.yahoo_estimates import YahooEstimateProvider


class FakeTicker:
    def __init__(
        self,
        earnings_estimate,
        info,
    ):
        self.earnings_estimate = earnings_estimate
        self.info = info


def _estimate_frame():
    return pd.DataFrame(
        {
            "avg": [2.16571, 2.36644],
            "numberOfAnalysts": [23, 23],
            "currency": ["EUR", "EUR"],
        },
        index=["0y", "+1y"],
    )


def test_yahoo_forward_eps_uses_next_year_consensus(
    monkeypatch,
):
    fake = FakeTicker(
        earnings_estimate=_estimate_frame(),
        info={
            "nextFiscalYearEnd": 1801353600,
        },
    )

    monkeypatch.setattr(
        "src.providers.yahoo_estimates.yf.Ticker",
        lambda symbol: fake,
    )

    record = YahooEstimateProvider().get_forward_eps_estimate(
        company_id=1,
        symbol="ITX.MC",
        estimate_date=date(2026, 9, 24),
    )

    assert record.metric == FinancialMetric.EPS
    assert record.value == pytest.approx(2.36644)
    assert record.currency == "EUR"
    assert record.fiscal_period_end == date(2027, 1, 31)
    assert record.estimate_date == date(2026, 9, 24)
    assert record.analyst_count == 23
    assert record.source_id is None


def test_yahoo_forward_eps_requires_next_year_row(
    monkeypatch,
):
    frame = _estimate_frame().drop(index="+1y")

    fake = FakeTicker(
        earnings_estimate=frame,
        info={
            "nextFiscalYearEnd": 1801353600,
        },
    )

    monkeypatch.setattr(
        "src.providers.yahoo_estimates.yf.Ticker",
        lambda symbol: fake,
    )

    with pytest.raises(
        ValueError,
        match=r"\+1y EPS estimate unavailable",
    ):
        YahooEstimateProvider().get_forward_eps_estimate(
            company_id=1,
            symbol="ITX.MC",
            estimate_date=date(2026, 9, 24),
        )


def test_yahoo_forward_eps_requires_fiscal_end(
    monkeypatch,
):
    fake = FakeTicker(
        earnings_estimate=_estimate_frame(),
        info={},
    )

    monkeypatch.setattr(
        "src.providers.yahoo_estimates.yf.Ticker",
        lambda symbol: fake,
    )

    with pytest.raises(
        ValueError,
        match="next fiscal year end unavailable",
    ):
        YahooEstimateProvider().get_forward_eps_estimate(
            company_id=1,
            symbol="ITX.MC",
            estimate_date=date(2026, 9, 24),
        )


def test_forward_eps_ingestion_is_idempotent(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "estimates.sqlite"
    initialize_database(db_path)

    fake = FakeTicker(
        earnings_estimate=_estimate_frame(),
        info={
            "nextFiscalYearEnd": 1801353600,
        },
    )

    monkeypatch.setattr(
        "src.providers.yahoo_estimates.yf.Ticker",
        lambda symbol: fake,
    )

    provider = YahooEstimateProvider()

    with managed_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO companies (
                company_id,
                name,
                ticker,
                exchange,
                currency
            )
            VALUES (1, 'Test Company', 'TST', 'BME', 'EUR')
            """
        )
        connection.commit()

        first_id = ingest_forward_eps_estimate(
            connection=connection,
            provider=provider,
            company_id=1,
            symbol="TST.MC",
            estimate_date=date(2026, 9, 24),
        )

        second_id = ingest_forward_eps_estimate(
            connection=connection,
            provider=provider,
            company_id=1,
            symbol="TST.MC",
            estimate_date=date(2026, 9, 24),
        )

        rows = connection.execute(
            """
            SELECT
                e.*,
                s.provider,
                s.document_type,
                s.confidence
            FROM estimates AS e
            JOIN sources AS s
                ON s.source_id = e.source_id
            """
        ).fetchall()

    assert second_id == first_id
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(2.36644)
    assert rows[0]["fiscal_period_end"] == "2027-01-31"
    assert rows[0]["estimate_date"] == "2026-09-24"
    assert rows[0]["analyst_count"] == 23
    assert rows[0]["provider"] == "yahoo"
    assert rows[0]["document_type"] == "forward_estimate"
    assert rows[0]["confidence"] == "secondary"
