from datetime import date

import pytest

from src.assessment import AssessmentLevel, RiskLevel
from src.backtest import (
    BacktestObservation,
    BacktestOutcome,
    build_backtest_signal,
)
from src.investment import AnalysisAvailability
from src.radar import RadarEntry, RadarScenario
from src.value import ValueCondition


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
            "Test Company",
            "TEST",
            "TESTEX",
            "EUR",
        ),
    )

    connection.commit()
    return cursor.lastrowid


def _entry() -> RadarEntry:
    return RadarEntry(
        company_id=1,
        name="Example Company",
        ticker="EX",
        exchange="TEST",
        as_of_date=date(2020, 1, 15),
        fiscal_period_end=date(2020, 12, 31),
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            RadarScenario(
                name="Base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
            RadarScenario(
                name="Stress",
                expected_return=0.04,
                required_price=40.0,
                price_margin=-0.20,
                condition=ValueCondition.TARGET_NOT_MET,
            ),
        ),
    )


def test_build_backtest_signal_copies_ex_ante_values():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    assert signal.company_id == 1
    assert signal.observation_date == date(2020, 1, 15)
    assert signal.scenario_name == "Base"
    assert signal.expected_return == pytest.approx(0.12)
    assert signal.required_price == pytest.approx(55.0)
    assert signal.price_margin == pytest.approx(0.10)
    assert signal.condition == ValueCondition.TARGET_MET


def test_build_backtest_signal_preserves_missing_values():
    entry = _entry()

    missing_scenario = RadarScenario(
        name="Unknown",
        expected_return=None,
        required_price=None,
        price_margin=None,
        condition=ValueCondition.UNKNOWN,
    )

    entry = RadarEntry(
        company_id=entry.company_id,
        name=entry.name,
        ticker=entry.ticker,
        exchange=entry.exchange,
        as_of_date=entry.as_of_date,
        fiscal_period_end=entry.fiscal_period_end,
        availability=entry.availability,
        quality_level=entry.quality_level,
        risk_level=entry.risk_level,
        value_trap_warning=entry.value_trap_warning,
        quality_reasons=entry.quality_reasons,
        risk_reasons=entry.risk_reasons,
        value_trap_reasons=entry.value_trap_reasons,
        scenarios=(missing_scenario,),
    )

    signal = build_backtest_signal(
        entry=entry,
        scenario_name="Unknown",
    )

    assert signal.expected_return is None
    assert signal.required_price is None
    assert signal.price_margin is None
    assert signal.condition == ValueCondition.UNKNOWN


def test_build_backtest_signal_rejects_unknown_scenario():
    with pytest.raises(
        ValueError,
        match="scenario not found",
    ):
        build_backtest_signal(
            entry=_entry(),
            scenario_name="Missing",
        )


def test_backtest_observation_accepts_future_outcome():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    outcome = BacktestOutcome(
        company_id=1,
        target_date=date(2021, 1, 15),
        price_date=date(2021, 1, 15),
        price=60.0,
    )

    observation = BacktestObservation(
        signal=signal,
        outcome=outcome,
    )

    assert observation.signal == signal
    assert observation.outcome == outcome


def test_backtest_observation_allows_missing_outcome():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    observation = BacktestObservation(
        signal=signal,
        outcome=None,
    )

    assert observation.outcome is None


def test_backtest_observation_rejects_different_company():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    outcome = BacktestOutcome(
        company_id=2,
        target_date=date(2021, 1, 15),
        price_date=date(2021, 1, 15),
        price=60.0,
    )

    with pytest.raises(
        ValueError,
        match="same company",
    ):
        BacktestObservation(
            signal=signal,
            outcome=outcome,
        )


def test_backtest_observation_rejects_non_future_target():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    outcome = BacktestOutcome(
        company_id=1,
        target_date=date(2020, 1, 15),
        price_date=date(2020, 1, 15),
        price=50.0,
    )

    with pytest.raises(
        ValueError,
        match="after observation_date",
    ):
        BacktestObservation(
            signal=signal,
            outcome=outcome,
        )


def test_backtest_observation_rejects_price_before_target():
    signal = build_backtest_signal(
        entry=_entry(),
        scenario_name="Base",
    )

    outcome = BacktestOutcome(
        company_id=1,
        target_date=date(2021, 1, 15),
        price_date=date(2021, 1, 14),
        price=60.0,
    )

    with pytest.raises(
        ValueError,
        match="cannot be before target_date",
    ):
        BacktestObservation(
            signal=signal,
            outcome=outcome,
        )


def test_build_backtest_outcome_uses_exact_target_date(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database
    from src.models import PriceRecord
    from src.repository import insert_price_record

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-01-15",
                close=60.0,
                currency="EUR",
            ),
        )

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 1, 15),
        )

    assert outcome is not None
    assert outcome.company_id == company_id
    assert outcome.target_date == date(2021, 1, 15)
    assert outcome.price_date == date(2021, 1, 15)
    assert outcome.price == pytest.approx(60.0)


def test_build_backtest_outcome_uses_next_available_session(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database
    from src.models import PriceRecord
    from src.repository import insert_price_record

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-01-18",
                close=61.0,
                currency="EUR",
            ),
        )

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 1, 16),
        )

    assert outcome is not None
    assert outcome.price_date == date(2021, 1, 18)
    assert outcome.price == pytest.approx(61.0)


def test_build_backtest_outcome_rejects_price_beyond_tolerance(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database
    from src.models import PriceRecord
    from src.repository import insert_price_record

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-01-25",
                close=62.0,
                currency="EUR",
            ),
        )

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 1, 15),
            max_days_after_target=7,
        )

    assert outcome is None


def test_build_backtest_outcome_returns_none_without_future_price(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database
    from src.models import PriceRecord
    from src.repository import insert_price_record

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-01-14",
                close=59.0,
                currency="EUR",
            ),
        )

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 1, 15),
        )

    assert outcome is None


def test_build_backtest_outcome_accepts_tolerance_boundary(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database
    from src.models import PriceRecord
    from src.repository import insert_price_record

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = _create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2021-01-22",
                close=63.0,
                currency="EUR",
            ),
        )

        outcome = build_backtest_outcome(
            connection=connection,
            company_id=company_id,
            target_date=date(2021, 1, 15),
            max_days_after_target=7,
        )

    assert outcome is not None
    assert outcome.price_date == date(2021, 1, 22)


def test_build_backtest_outcome_rejects_invalid_company_id(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(
            ValueError,
            match="company_id must be greater than zero",
        ):
            build_backtest_outcome(
                connection=connection,
                company_id=0,
                target_date=date(2021, 1, 15),
            )


def test_build_backtest_outcome_rejects_negative_tolerance(
    tmp_path,
):
    from src.backtest import build_backtest_outcome
    from src.db import connect, initialize_database

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(
            ValueError,
            match="cannot be negative",
        ):
            build_backtest_outcome(
                connection=connection,
                company_id=1,
                target_date=date(2021, 1, 15),
                max_days_after_target=-1,
            )
