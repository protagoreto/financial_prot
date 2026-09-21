from dataclasses import dataclass
from datetime import date
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