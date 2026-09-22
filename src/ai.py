from dataclasses import dataclass
from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import RadarEntry
from src.value import ValueCondition


@dataclass(frozen=True)
class AIValueScenario:
    name: str
    expected_return: float | None
    required_price: float | None
    price_margin: float | None
    condition: ValueCondition


@dataclass(frozen=True)
class AIAnalysisContext:
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

    scenarios: tuple[AIValueScenario, ...]


def build_ai_analysis_context(
    entry: RadarEntry,
) -> AIAnalysisContext:
    return AIAnalysisContext(
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
        scenarios=tuple(
            AIValueScenario(
                name=scenario.name,
                expected_return=scenario.expected_return,
                required_price=scenario.required_price,
                price_margin=scenario.price_margin,
                condition=scenario.condition,
            )
            for scenario in entry.scenarios
        ),
    )
