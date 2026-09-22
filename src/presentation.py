from dataclasses import dataclass
from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar_report import RadarReportRow
from src.value import ValueCondition


@dataclass(frozen=True)
class AnalysisPresentation:
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


def build_analysis_presentation(
    row: RadarReportRow,
) -> AnalysisPresentation:
    return AnalysisPresentation(
        company_id=row.company_id,
        name=row.name,
        ticker=row.ticker,
        exchange=row.exchange,
        as_of_date=row.as_of_date,
        fiscal_period_end=row.fiscal_period_end,
        target_return=row.target_return,
        years=row.years,
        availability=row.availability,
        quality_level=row.quality_level,
        risk_level=row.risk_level,
        value_trap_warning=row.value_trap_warning,
        scenario_name=row.scenario_name,
        expected_return=row.expected_return,
        required_price=row.required_price,
        price_margin=row.price_margin,
        condition=row.condition,
    )
