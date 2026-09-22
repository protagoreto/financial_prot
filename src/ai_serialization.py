from typing import Any

from src.ai import AIAnalysisContext


def serialize_ai_analysis_context(
    context: AIAnalysisContext,
) -> dict[str, Any]:
    return {
        "company": {
            "company_id": context.company_id,
            "name": context.name,
            "ticker": context.ticker,
            "exchange": context.exchange,
        },
        "point_in_time": {
            "as_of_date": context.as_of_date.isoformat(),
            "fiscal_period_end": (
                context.fiscal_period_end.isoformat()
            ),
        },
        "analysis": {
            "availability": context.availability.value,
            "quality": {
                "level": (
                    context.quality_level.value
                    if context.quality_level is not None
                    else None
                ),
                "reasons": list(context.quality_reasons),
            },
            "risk": {
                "level": (
                    context.risk_level.value
                    if context.risk_level is not None
                    else None
                ),
                "reasons": list(context.risk_reasons),
            },
            "value_trap": {
                "warning": context.value_trap_warning,
                "reasons": list(
                    context.value_trap_reasons
                ),
            },
            "scenarios": [
                {
                    "name": scenario.name,
                    "expected_return": (
                        scenario.expected_return
                    ),
                    "required_price": (
                        scenario.required_price
                    ),
                    "price_margin": scenario.price_margin,
                    "condition": scenario.condition.value,
                }
                for scenario in context.scenarios
            ],
        },
    }
