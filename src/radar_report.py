from dataclasses import dataclass
from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import RadarEntry, RadarSnapshot
from src.value import ValueCondition


@dataclass(frozen=True)
class RadarReportRow:
    company_id: int
    name: str
    ticker: str | None
    exchange: str | None

    as_of_date: date
    fiscal_period_end: date
    target_return: float
    years: int

    availability: AnalysisAvailability

    quality_level: AssessmentLevel | None
    risk_level: RiskLevel | None
    value_trap_warning: bool | None

    scenario_name: str
    expected_return: float | None
    required_price: float | None
    price_margin: float | None
    condition: ValueCondition | None


def build_radar_report(
    snapshot: RadarSnapshot,
    scenario_name: str,
    entries: tuple[RadarEntry, ...] | None = None,
) -> tuple[RadarReportRow, ...]:
    normalized_scenario_name = scenario_name.strip()

    if not normalized_scenario_name:
        raise ValueError(
            "Radar report requires a non-empty scenario_name."
        )

    selected_entries = (
        snapshot.entries
        if entries is None
        else entries
    )

    return tuple(
        _build_radar_report_row(
            entry=entry,
            snapshot=snapshot,
            scenario_name=normalized_scenario_name,
        )
        for entry in selected_entries
    )


def _build_radar_report_row(
    entry: RadarEntry,
    snapshot: RadarSnapshot,
    scenario_name: str,
) -> RadarReportRow:
    matching_scenarios = tuple(
        scenario
        for scenario in entry.scenarios
        if scenario.name == scenario_name
    )

    if len(matching_scenarios) > 1:
        raise ValueError(
            "Radar entry contains duplicate scenario names."
        )

    if matching_scenarios:
        scenario = matching_scenarios[0]
        expected_return = scenario.expected_return
        required_price = scenario.required_price
        price_margin = scenario.price_margin
        condition = scenario.condition
    else:
        expected_return = None
        required_price = None
        price_margin = None
        condition = None

    return RadarReportRow(
        company_id=entry.company_id,
        name=entry.name,
        ticker=entry.ticker,
        exchange=entry.exchange,
        as_of_date=entry.as_of_date,
        fiscal_period_end=entry.fiscal_period_end,
        target_return=snapshot.target_return,
        years=snapshot.years,
        availability=entry.availability,
        quality_level=entry.quality_level,
        risk_level=entry.risk_level,
        value_trap_warning=entry.value_trap_warning,
        scenario_name=scenario_name,
        expected_return=expected_return,
        required_price=required_price,
        price_margin=price_margin,
        condition=condition,
    )