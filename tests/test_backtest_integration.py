from datetime import date

import pytest

from src.backtest import (
    build_backtest_outcome,
    build_backtest_realized_observation,
    build_backtest_series,
    summarize_backtest,
)
from src.db import connect, initialize_database
from src.models import EstimateRecord, PriceRecord
from src.repository import (
    insert_estimate_record,
    insert_price_record,
)
from src.scenarios import ValuationScenario


def _create_company(connection) -> int:
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
            "Backtest Integration Company",
            "BTI",
            "TESTEX",
            "EUR",
        ),
    )
    connection.commit()
    return cursor.lastrowid


def test_backtest_end_to_end_is_point_in_time(tmp_path):
    db_path = tmp_path / "backtest.sqlite"
    initialize_database(db_path)

    scenarios = (
        ValuationScenario(
            name="Base",
            eps_growth=0.08,
            dividend_yield=0.02,
            terminal_pe=15.0,
        ),
    )

    observation_dates = (
        date(2020, 1, 15),
        date(2020, 2, 15),
    )

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2020-01-15",
                close=50.0,
                currency="EUR",
            ),
        )
        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2020-02-14",
                close=55.0,
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
                fiscal_period_end="2020-12-31",
                estimate_date="2020-02-01",
                analyst_count=10,
            ),
        )

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-02-15",
                close=66.0,
                currency="EUR",
            ),
        )

        series = build_backtest_series(
            connection=connection,
            company_id=company_id,
            observation_dates=observation_dates,
            scenarios=scenarios,
            scenario_name="Base",
        )

        assert len(series.points) == 2

        first = series.points[0]
        second = series.points[1]

        # The estimate was not known on 2020-01-15.
        assert first.snapshot is None

        # The estimate was known by 2020-02-15.
        assert second.snapshot is not None
        assert second.snapshot.observation_date == date(
            2020,
            2,
            15,
        )
        assert second.snapshot.price_date == date(
            2020,
            2,
            14,
        )
        assert second.snapshot.price == pytest.approx(55.0)
        assert second.snapshot.estimate_date == date(
            2020,
            2,
            1,
        )
        assert second.snapshot.forward_eps == pytest.approx(3.0)

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 2, 15),
        )

        assert outcome is not None
        assert outcome.price_date == date(2021, 2, 15)
        assert outcome.price == pytest.approx(66.0)

        realized = build_backtest_realized_observation(
            snapshot=second.snapshot,
            outcome=outcome,
        )

        summary = summarize_backtest(
            (
                None,
                realized,
            )
        )

    assert realized.price_return == pytest.approx(0.20)

    assert summary.observation_count == 2
    assert summary.realized_count == 1
    assert summary.positive_count == 1
    assert summary.mean_price_return == pytest.approx(0.20)
    assert summary.median_price_return == pytest.approx(0.20)
    assert summary.positive_rate == pytest.approx(1.0)
