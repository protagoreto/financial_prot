from dataclasses import dataclass
from datetime import date
from enum import Enum
import sqlite3

from src.assessment import (
    AssessmentLevel,
    AssessmentPolicy,
    RiskLevel,
)
from src.investment import (
    AnalysisAvailability,
    build_investment_analysis,
)
from src.repository import get_company_by_id
from src.scenarios import ValuationScenario
from src.value import ValueCondition


@dataclass(frozen=True)
class RadarCompanyInput:
    company_id: int
    fiscal_period_end: date


@dataclass(frozen=True)
class RadarScenario:
    name: str
    expected_return: float | None
    required_price: float | None
    price_margin: float | None
    condition: ValueCondition


@dataclass(frozen=True)
class RadarEntry:
    company_id: int
    name: str
    ticker: str | None
    exchange: str | None
    as_of_date: date
    fiscal_period_end: date

    availability: AnalysisAvailability

    quality_level: AssessmentLevel | None
    risk_level: RiskLevel | None
    value_trap_warning: bool | None

    quality_reasons: tuple[str, ...]
    risk_reasons: tuple[str, ...]
    value_trap_reasons: tuple[str, ...]

    scenarios: tuple[RadarScenario, ...]


@dataclass(frozen=True)
class RadarSnapshot:
    as_of_date: date
    target_return: float
    years: int
    entries: tuple[RadarEntry, ...]


def build_radar_snapshot(
    connection: sqlite3.Connection,
    companies: tuple[RadarCompanyInput, ...],
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float = 0.10,
    years: int = 5,
    assessment_policy: AssessmentPolicy = AssessmentPolicy(),
    low_net_debt_threshold: float = 2.0,
) -> RadarSnapshot:
    if target_return <= -1.0:
        raise ValueError(
            "target_return must be greater than -1."
        )

    if years <= 0:
        raise ValueError(
            "years must be greater than zero."
        )

    company_ids = [
        company.company_id
        for company in companies
    ]

    if any(company_id <= 0 for company_id in company_ids):
        raise ValueError(
            "company_id must be greater than zero."
        )

    if len(company_ids) != len(set(company_ids)):
        raise ValueError(
            "Radar companies must be unique."
        )

    entries = tuple(
        _build_radar_entry(
            connection=connection,
            company=company,
            as_of_date=as_of_date,
            scenarios=scenarios,
            target_return=target_return,
            years=years,
            assessment_policy=assessment_policy,
            low_net_debt_threshold=low_net_debt_threshold,
        )
        for company in companies
    )

    return RadarSnapshot(
        as_of_date=as_of_date,
        target_return=target_return,
        years=years,
        entries=entries,
    )


def _build_radar_entry(
    connection: sqlite3.Connection,
    company: RadarCompanyInput,
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float,
    years: int,
    assessment_policy: AssessmentPolicy,
    low_net_debt_threshold: float,
) -> RadarEntry:
    company_record = get_company_by_id(
        connection=connection,
        company_id=company.company_id,
    )

    if company_record is None:
        raise ValueError(
            "Radar company does not exist."
        )

    analysis = build_investment_analysis(
        connection=connection,
        company_id=company.company_id,
        as_of_date=as_of_date,
        fiscal_period_end=company.fiscal_period_end,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
        assessment_policy=assessment_policy,
        low_net_debt_threshold=low_net_debt_threshold,
    )

    fundamentals = analysis.fundamentals

    if fundamentals is None:
        quality_level = None
        risk_level = None
        value_trap_warning = None
        quality_reasons = ()
        risk_reasons = ()
        value_trap_reasons = ()
    else:
        quality_level = fundamentals.quality_level
        risk_level = fundamentals.risk_level
        value_trap_warning = (
            fundamentals.value_trap_warning
        )
        quality_reasons = fundamentals.quality_reasons
        risk_reasons = fundamentals.risk_reasons
        value_trap_reasons = (
            fundamentals.value_trap_reasons
        )

    radar_scenarios = (
        tuple(
            RadarScenario(
                name=scenario.name,
                expected_return=scenario.expected_return,
                required_price=scenario.required_price,
                price_margin=scenario.price_margin,
                condition=scenario.condition,
            )
            for scenario in analysis.value.scenarios
        )
        if analysis.value is not None
        else ()
    )

    return RadarEntry(
        company_id=company.company_id,
        name=company_record.name,
        ticker=company_record.ticker,
        exchange=company_record.exchange,
        as_of_date=as_of_date,
        fiscal_period_end=company.fiscal_period_end,
        availability=analysis.availability,
        quality_level=quality_level,
        risk_level=risk_level,
        value_trap_warning=value_trap_warning,
        quality_reasons=quality_reasons,
        risk_reasons=risk_reasons,
        value_trap_reasons=value_trap_reasons,
        scenarios=radar_scenarios,
    )


@dataclass(frozen=True)
class RadarFilter:
    availability: AnalysisAvailability | None = None
    quality_level: AssessmentLevel | None = None
    risk_level: RiskLevel | None = None
    value_trap_warning: bool | None = None

    scenario_name: str | None = None
    condition: ValueCondition | None = None
    min_expected_return: float | None = None
    min_price_margin: float | None = None

    def is_valid(self) -> bool:
        has_scenario_criterion = any(
            criterion is not None
            for criterion in (
                self.condition,
                self.min_expected_return,
                self.min_price_margin,
            )
        )

        if has_scenario_criterion and self.scenario_name is None:
            return False

        if (
            self.scenario_name is not None
            and not self.scenario_name.strip()
        ):
            return False

        return True


def filter_radar_entries(
    snapshot: RadarSnapshot,
    radar_filter: RadarFilter,
) -> tuple[RadarEntry, ...]:
    if not radar_filter.is_valid():
        raise ValueError(
            "Scenario criteria require a non-empty scenario_name."
        )

    return tuple(
        entry
        for entry in snapshot.entries
        if _matches_radar_filter(
            entry=entry,
            radar_filter=radar_filter,
        )
    )


def _matches_radar_filter(
    entry: RadarEntry,
    radar_filter: RadarFilter,
) -> bool:
    if (
        radar_filter.availability is not None
        and entry.availability != radar_filter.availability
    ):
        return False

    if (
        radar_filter.quality_level is not None
        and entry.quality_level != radar_filter.quality_level
    ):
        return False

    if (
        radar_filter.risk_level is not None
        and entry.risk_level != radar_filter.risk_level
    ):
        return False

    if (
        radar_filter.value_trap_warning is not None
        and entry.value_trap_warning
        is not radar_filter.value_trap_warning
    ):
        return False

    if radar_filter.scenario_name is None:
        return True

    scenario = _get_radar_scenario(
        entry=entry,
        scenario_name=radar_filter.scenario_name,
    )

    if scenario is None:
        return False

    if (
        radar_filter.condition is not None
        and scenario.condition != radar_filter.condition
    ):
        return False

    if radar_filter.min_expected_return is not None:
        if scenario.expected_return is None:
            return False

        if (
            scenario.expected_return
            < radar_filter.min_expected_return
        ):
            return False

    if radar_filter.min_price_margin is not None:
        if scenario.price_margin is None:
            return False

        if (
            scenario.price_margin
            < radar_filter.min_price_margin
        ):
            return False

    return True


def _get_radar_scenario(
    entry: RadarEntry,
    scenario_name: str,
) -> RadarScenario | None:
    matching = tuple(
        scenario
        for scenario in entry.scenarios
        if scenario.name == scenario_name
    )

    if len(matching) > 1:
        raise ValueError(
            "Radar entry contains duplicate scenario names."
        )

    if not matching:
        return None

    return matching[0]


class RadarSortMetric(str, Enum):
    EXPECTED_RETURN = "expected_return"
    PRICE_MARGIN = "price_margin"
    REQUIRED_PRICE = "required_price"


class RadarSortDirection(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


@dataclass(frozen=True)
class RadarSort:
    metric: RadarSortMetric
    scenario_name: str
    direction: RadarSortDirection = (
        RadarSortDirection.DESCENDING
    )

    def is_valid(self) -> bool:
        return bool(self.scenario_name.strip())


def sort_radar_entries(
    entries: tuple[RadarEntry, ...],
    radar_sort: RadarSort,
) -> tuple[RadarEntry, ...]:
    if not radar_sort.is_valid():
        raise ValueError(
            "Radar sorting requires a non-empty scenario_name."
        )

    available: list[tuple[RadarEntry, float]] = []
    unavailable: list[RadarEntry] = []

    for entry in entries:
        scenario = _get_radar_scenario(
            entry=entry,
            scenario_name=radar_sort.scenario_name,
        )

        if scenario is None:
            unavailable.append(entry)
            continue

        value = _get_radar_sort_value(
            scenario=scenario,
            metric=radar_sort.metric,
        )

        if value is None:
            unavailable.append(entry)
            continue

        available.append((entry, value))

    if radar_sort.direction == RadarSortDirection.DESCENDING:
        ordered_available = sorted(
            available,
            key=lambda item: (
                -item[1],
                item[0].company_id,
            ),
        )
    else:
        ordered_available = sorted(
            available,
            key=lambda item: (
                item[1],
                item[0].company_id,
            ),
        )

    ordered_unavailable = sorted(
        unavailable,
        key=lambda entry: entry.company_id,
    )

    return tuple(
        entry
        for entry, _ in ordered_available
    ) + tuple(ordered_unavailable)


def _get_radar_sort_value(
    scenario: RadarScenario,
    metric: RadarSortMetric,
) -> float | None:
    if metric == RadarSortMetric.EXPECTED_RETURN:
        return scenario.expected_return

    if metric == RadarSortMetric.PRICE_MARGIN:
        return scenario.price_margin

    if metric == RadarSortMetric.REQUIRED_PRICE:
        return scenario.required_price

    raise ValueError(
        f"Unsupported radar sort metric: {metric!r}."
    )