from dataclasses import dataclass
from datetime import date

from src.radar import RadarEntry, RadarScenario
from src.value import ValueCondition


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
    scenario = _get_scenario(
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


def _get_scenario(
    entry: RadarEntry,
    scenario_name: str,
) -> RadarScenario:
    for scenario in entry.scenarios:
        if scenario.name == scenario_name:
            return scenario

    raise ValueError(
        f"scenario not found: {scenario_name}"
    )
