from dataclasses import dataclass
from datetime import date
import sqlite3
from statistics import mean, median

from src.analysis import (
    ValuationAnalysis,
    build_valuation_analysis,
)
from src.metrics import FinancialMetric
from src.radar import RadarEntry, RadarScenario
from src.repository import (
    get_next_estimate_period_on_or_after,
    get_price_on_or_after,
)
from src.scenarios import ValuationScenario
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
class BacktestSeriesPoint:
    observation_date: date
    snapshot: BacktestExAnteSnapshot | None

    def __post_init__(self) -> None:
        if (
            self.snapshot is not None
            and self.snapshot.observation_date
            != self.observation_date
        ):
            raise ValueError(
                "snapshot and series point must have "
                "the same observation_date."
            )


@dataclass(frozen=True)
class BacktestSeries:
    company_id: int
    scenario_name: str
    points: tuple[BacktestSeriesPoint, ...]

    def __post_init__(self) -> None:
        if self.company_id <= 0:
            raise ValueError(
                "company_id must be greater than zero."
            )

        if not self.scenario_name.strip():
            raise ValueError(
                "scenario_name cannot be blank."
            )

        previous_date: date | None = None

        for point in self.points:
            if (
                previous_date is not None
                and point.observation_date <= previous_date
            ):
                raise ValueError(
                    "series observation dates must be "
                    "strictly increasing."
                )

            if (
                point.snapshot is not None
                and point.snapshot.company_id
                != self.company_id
            ):
                raise ValueError(
                    "series snapshot must belong to "
                    "the series company."
                )

            if (
                point.snapshot is not None
                and point.snapshot.signal.scenario_name
                != self.scenario_name
            ):
                raise ValueError(
                    "series snapshot must use "
                    "the series scenario."
                )

            previous_date = point.observation_date


@dataclass(frozen=True)
class BacktestOutcome:
    company_id: int
    target_date: date
    price_date: date
    price: float

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError(
                "outcome price must be greater than zero."
            )


@dataclass(frozen=True)
class BacktestRealizedObservation:
    snapshot: BacktestExAnteSnapshot
    outcome: BacktestOutcome

    def __post_init__(self) -> None:
        if self.snapshot.company_id != self.outcome.company_id:
            raise ValueError(
                "snapshot and outcome must belong to "
                "the same company."
            )

        if (
            self.outcome.target_date
            <= self.snapshot.observation_date
        ):
            raise ValueError(
                "outcome target_date must be after "
                "observation_date."
            )

        if self.outcome.price_date < self.outcome.target_date:
            raise ValueError(
                "outcome price_date cannot be before "
                "target_date."
            )

        if self.snapshot.price <= 0:
            raise ValueError(
                "snapshot price must be greater than zero."
            )

    @property
    def price_return(self) -> float:
        return self.outcome.price / self.snapshot.price - 1


@dataclass(frozen=True)
class BacktestSummary:
    observation_count: int
    realized_count: int
    positive_count: int
    mean_price_return: float | None
    median_price_return: float | None
    positive_rate: float | None


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


def build_backtest_series(
    connection: sqlite3.Connection,
    company_id: int,
    observation_dates: tuple[date, ...],
    scenarios: tuple[ValuationScenario, ...],
    scenario_name: str,
    target_return: float = 0.10,
    years: int = 5,
) -> BacktestSeries:
    if company_id <= 0:
        raise ValueError(
            "company_id must be greater than zero."
        )

    if not scenario_name.strip():
        raise ValueError(
            "scenario_name cannot be blank."
        )

    if years <= 0:
        raise ValueError(
            "years must be greater than zero."
        )

    if target_return <= -1:
        raise ValueError(
            "target_return must be greater than -1."
        )

    if any(
        current <= previous
        for previous, current in zip(
            observation_dates,
            observation_dates[1:],
        )
    ):
        raise ValueError(
            "observation_dates must be strictly increasing."
        )

    if not any(
        scenario.name == scenario_name
        for scenario in scenarios
    ):
        raise ValueError(
            f"scenario not found: {scenario_name}"
        )

    points: list[BacktestSeriesPoint] = []

    for observation_date in observation_dates:
        fiscal_period_end = (
            get_next_estimate_period_on_or_after(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                as_of_date=observation_date,
            )
        )

        if fiscal_period_end is None:
            points.append(
                BacktestSeriesPoint(
                    observation_date=observation_date,
                    snapshot=None,
                )
            )
            continue

        valuation = build_valuation_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=observation_date,
            fiscal_period_end=fiscal_period_end,
            scenarios=scenarios,
            target_return=target_return,
            years=years,
        )

        if valuation is None:
            points.append(
                BacktestSeriesPoint(
                    observation_date=observation_date,
                    snapshot=None,
                )
            )
            continue

        snapshot = build_backtest_ex_ante_snapshot(
            valuation=valuation,
            scenario_name=scenario_name,
        )

        points.append(
            BacktestSeriesPoint(
                observation_date=observation_date,
                snapshot=snapshot,
            )
        )

    return BacktestSeries(
        company_id=company_id,
        scenario_name=scenario_name,
        points=tuple(points),
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


def build_backtest_realized_observation(
    snapshot: BacktestExAnteSnapshot,
    outcome: BacktestOutcome,
) -> BacktestRealizedObservation:
    return BacktestRealizedObservation(
        snapshot=snapshot,
        outcome=outcome,
    )


def summarize_backtest(
    observations: tuple[
        BacktestRealizedObservation | None,
        ...,
    ],
) -> BacktestSummary:
    realized = tuple(
        observation
        for observation in observations
        if observation is not None
    )

    if not realized:
        return BacktestSummary(
            observation_count=len(observations),
            realized_count=0,
            positive_count=0,
            mean_price_return=None,
            median_price_return=None,
            positive_rate=None,
        )

    returns = tuple(
        observation.price_return
        for observation in realized
    )

    positive_count = sum(
        price_return > 0
        for price_return in returns
    )

    return BacktestSummary(
        observation_count=len(observations),
        realized_count=len(realized),
        positive_count=positive_count,
        mean_price_return=mean(returns),
        median_price_return=median(returns),
        positive_rate=(
            positive_count / len(realized)
        ),
    )
