from dataclasses import dataclass
from datetime import date
import sqlite3

from src.analysis import ValuationAnalysis
from src.radar import RadarEntry, RadarScenario
from src.repository import get_price_on_or_after
from src.value import (
    ScenarioValueAssessment,
    ValueCondition,
    assess_value,
)


@dataclass(frozen=True)
class BacktestSignal:
    company_id: int
    observation_date: date
    scenario_name: str
    expected_return: float | None
    required_price: float | None
    price_margin: float | None
    condition: ValueCondition


@dataclass(frozen=True)
class BacktestExAnteSnapshot:
    company_id: int
    observation_date: date
    price_date: date
    price: float
    fiscal_period_end: date
    estimate_date: date
    analyst_count: int | None
    forward_eps: float
    forward_pe: float | None
    forward_earnings_yield: float | None
    signal: BacktestSignal

    def __post_init__(self) -> None:
        if self.price_date > self.observation_date:
            raise ValueError(
                "price_date cannot be after observation_date."
            )

        if self.estimate_date > self.observation_date:
            raise ValueError(
                "estimate_date cannot be after observation_date."
            )

        if self.signal.company_id != self.company_id:
            raise ValueError(
                "signal and snapshot must belong to the same company."
            )

        if self.signal.observation_date != self.observation_date:
            raise ValueError(
                "signal and snapshot must have the same observation_date."
            )


@dataclass(frozen=True)
class BacktestOutcome:
    company_id: int
    target_date: date
    price_date: date
    price: float


@dataclass(frozen=True)
class BacktestObservation:
    signal: BacktestSignal
    outcome: BacktestOutcome | None

    def __post_init__(self) -> None:
        if self.outcome is None:
            return

        if self.signal.company_id != self.outcome.company_id:
            raise ValueError(
                "signal and outcome must belong to the same company."
            )

        if self.outcome.target_date <= self.signal.observation_date:
            raise ValueError(
                "outcome target_date must be after observation_date."
            )

        if self.outcome.price_date < self.outcome.target_date:
            raise ValueError(
                "outcome price_date cannot be before target_date."
            )


def build_backtest_signal(
    entry: RadarEntry,
    scenario_name: str,
) -> BacktestSignal:
    scenario = _get_radar_scenario(
        entry=entry,
        scenario_name=scenario_name,
    )

    return BacktestSignal(
        company_id=entry.company_id,
        observation_date=entry.as_of_date,
        scenario_name=scenario.name,
        expected_return=scenario.expected_return,
        required_price=scenario.required_price,
        price_margin=scenario.price_margin,
        condition=scenario.condition,
    )


def build_backtest_ex_ante_snapshot(
    valuation: ValuationAnalysis,
    scenario_name: str,
) -> BacktestExAnteSnapshot:
    assessment = assess_value(valuation)

    scenario = _get_value_scenario(
        scenarios=assessment.scenarios,
        scenario_name=scenario_name,
    )

    signal = BacktestSignal(
        company_id=valuation.company_id,
        observation_date=valuation.as_of_date,
        scenario_name=scenario.name,
        expected_return=scenario.expected_return,
        required_price=scenario.required_price,
        price_margin=scenario.price_margin,
        condition=scenario.condition,
    )

    snapshot = valuation.snapshot

    return BacktestExAnteSnapshot(
        company_id=valuation.company_id,
        observation_date=valuation.as_of_date,
        price_date=snapshot.price_date,
        price=snapshot.price,
        fiscal_period_end=snapshot.fiscal_period_end,
        estimate_date=snapshot.estimate_date,
        analyst_count=snapshot.analyst_count,
        forward_eps=snapshot.forward_eps,
        forward_pe=snapshot.forward_pe,
        forward_earnings_yield=snapshot.forward_earnings_yield,
        signal=signal,
    )


def _get_radar_scenario(
    entry: RadarEntry,
    scenario_name: str,
) -> RadarScenario:
    for scenario in entry.scenarios:
        if scenario.name == scenario_name:
            return scenario

    raise ValueError(
        f"scenario not found: {scenario_name}"
    )


def _get_value_scenario(
    scenarios: tuple[ScenarioValueAssessment, ...],
    scenario_name: str,
) -> ScenarioValueAssessment:
    for scenario in scenarios:
        if scenario.name == scenario_name:
            return scenario

    raise ValueError(
        f"scenario not found: {scenario_name}"
    )


def build_backtest_outcome(
    connection: sqlite3.Connection,
    company_id: int,
    target_date: date,
    max_days_after_target: int = 7,
) -> BacktestOutcome | None:
    if company_id <= 0:
        raise ValueError(
            "company_id must be greater than zero."
        )

    if max_days_after_target < 0:
        raise ValueError(
            "max_days_after_target cannot be negative."
        )

    price = get_price_on_or_after(
        connection=connection,
        company_id=company_id,
        target_date=target_date,
    )

    if price is None:
        return None

    days_after_target = (
        price.price_date - target_date
    ).days

    if days_after_target > max_days_after_target:
        return None

    return BacktestOutcome(
        company_id=company_id,
        target_date=target_date,
        price_date=price.price_date,
        price=price.close,
    )
