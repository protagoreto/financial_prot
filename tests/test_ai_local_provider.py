import json
from datetime import date

import pytest

from src.ai import (
    AIAnalysisContext,
    AIValueScenario,
)
from src.ai_prompt import AIPrompt, build_ai_prompt
from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.providers.ai_base import AIProvider
from src.providers.ai_local import LocalAIProvider
from src.value import ValueCondition


def _context() -> AIAnalysisContext:
    return AIAnalysisContext(
        company_id=1,
        name="Test Company",
        ticker="TEST",
        exchange="BME",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=(
            "positive_net_income",
            "positive_free_cash_flow",
        ),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            AIValueScenario(
                name="Base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
        ),
    )


def test_local_provider_implements_ai_provider():
    provider = LocalAIProvider()

    assert isinstance(provider, AIProvider)
    assert provider.name == "local"


def test_local_provider_generates_valid_narrative():
    provider = LocalAIProvider()

    narrative = provider.generate_analysis(
        build_ai_prompt(_context())
    )

    assert narrative.is_valid()
    assert "Test Company" in narrative.summary
    assert "2026-09-22" in narrative.summary
    assert "complete" in narrative.summary


def test_local_provider_preserves_assessment_values():
    provider = LocalAIProvider()

    narrative = provider.generate_analysis(
        build_ai_prompt(_context())
    )

    assert "strong" in narrative.quality_commentary
    assert (
        "positive_net_income"
        in narrative.quality_commentary
    )
    assert "low" in narrative.risk_commentary


def test_local_provider_preserves_scenario_values():
    provider = LocalAIProvider()

    narrative = provider.generate_analysis(
        build_ai_prompt(_context())
    )

    assert "Base" in narrative.valuation_commentary
    assert "0.12" in narrative.valuation_commentary
    assert "55.0" in narrative.valuation_commentary
    assert "0.1" in narrative.valuation_commentary
    assert (
        "target_met"
        in narrative.valuation_commentary
    )


def test_local_provider_does_not_add_limitations_when_complete():
    provider = LocalAIProvider()

    narrative = provider.generate_analysis(
        build_ai_prompt(_context())
    )

    assert narrative.limitations == ()


def test_local_provider_preserves_missing_values():
    context = AIAnalysisContext(
        company_id=1,
        name="Incomplete Company",
        ticker=None,
        exchange=None,
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.INSUFFICIENT,
        quality_level=None,
        risk_level=None,
        value_trap_warning=None,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            AIValueScenario(
                name="Unknown",
                expected_return=None,
                required_price=None,
                price_margin=None,
                condition=ValueCondition.UNKNOWN,
            ),
        ),
    )

    narrative = LocalAIProvider().generate_analysis(
        build_ai_prompt(context)
    )

    assert "unavailable" in narrative.quality_commentary
    assert "unavailable" in narrative.risk_commentary

    assert (
        "expected_return=unavailable"
        in narrative.valuation_commentary
    )
    assert (
        "required_price=unavailable"
        in narrative.valuation_commentary
    )
    assert (
        "price_margin=unavailable"
        in narrative.valuation_commentary
    )
    assert "condition=unknown" in (
        narrative.valuation_commentary
    )

    assert (
        "Analysis availability is not complete."
        in narrative.limitations
    )
    assert (
        "Quality assessment is unavailable."
        in narrative.limitations
    )
    assert (
        "Risk assessment is unavailable."
        in narrative.limitations
    )
    assert (
        "Value-trap assessment is unavailable."
        in narrative.limitations
    )
    assert (
        "At least one valuation scenario "
        "has an unknown value condition."
        in narrative.limitations
    )


def test_local_provider_handles_no_scenarios():
    context = AIAnalysisContext(
        company_id=1,
        name="No Scenario Company",
        ticker=None,
        exchange=None,
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.INSUFFICIENT,
        quality_level=None,
        risk_level=None,
        value_trap_warning=None,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(),
    )

    narrative = LocalAIProvider().generate_analysis(
        build_ai_prompt(context)
    )

    assert narrative.valuation_commentary == (
        "No valuation scenarios are available "
        "in the supplied context."
    )
    assert (
        "No valuation scenarios are available."
        in narrative.limitations
    )


def test_local_provider_rejects_invalid_prompt():
    prompt = AIPrompt(
        instructions="instructions",
        context_json="not-json",
    )

    with pytest.raises(
        ValueError,
        match="invalid prompt",
    ):
        LocalAIProvider().generate_analysis(prompt)


def test_local_provider_rejects_invalid_context_shape():
    prompt = AIPrompt(
        instructions="instructions",
        context_json=json.dumps(
            {
                "company": [],
                "point_in_time": {},
                "analysis": {},
            }
        ),
    )

    with pytest.raises(
        ValueError,
        match="'company' must be an object",
    ):
        LocalAIProvider().generate_analysis(prompt)
