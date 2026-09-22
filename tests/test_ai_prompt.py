import json
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.ai import (
    AIAnalysisContext,
    AIValueScenario,
)
from src.ai_prompt import (
    AIPrompt,
    AI_SYSTEM_INSTRUCTIONS,
    build_ai_prompt,
)
from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
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


def test_build_ai_prompt_is_deterministic():
    context = _context()

    first = build_ai_prompt(context)
    second = build_ai_prompt(context)

    assert first == second


def test_build_ai_prompt_uses_fixed_instructions():
    prompt = build_ai_prompt(_context())

    assert prompt.instructions == AI_SYSTEM_INSTRUCTIONS
    assert prompt.instructions.strip()


def test_build_ai_prompt_contains_serialized_context():
    prompt = build_ai_prompt(_context())

    decoded = json.loads(prompt.context_json)

    assert decoded["company"]["company_id"] == 1
    assert decoded["company"]["name"] == "Test Company"
    assert (
        decoded["analysis"]["availability"]
        == "complete"
    )

    scenario = decoded["analysis"]["scenarios"][0]

    assert scenario["expected_return"] == 0.12
    assert scenario["required_price"] == 55.0
    assert scenario["price_margin"] == 0.10
    assert scenario["condition"] == "target_met"


def test_build_ai_prompt_preserves_missing_values():
    context = AIAnalysisContext(
        company_id=2,
        name="Missing Data Company",
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

    prompt = build_ai_prompt(context)
    decoded = json.loads(prompt.context_json)

    assert decoded["company"]["ticker"] is None
    assert decoded["analysis"]["quality"]["level"] is None
    assert decoded["analysis"]["risk"]["level"] is None
    assert (
        decoded["analysis"]["value_trap"]["warning"]
        is None
    )

    scenario = decoded["analysis"]["scenarios"][0]

    assert scenario["expected_return"] is None
    assert scenario["required_price"] is None
    assert scenario["price_margin"] is None
    assert scenario["condition"] == "unknown"


def test_ai_instructions_prohibit_financial_recalculation():
    instructions = AI_SYSTEM_INSTRUCTIONS.lower()

    assert "do not calculate or recalculate" in instructions
    assert "do not create, estimate" in instructions
    assert "do not create a new valuation" in instructions


def test_ai_instructions_protect_missing_and_unknown_values():
    instructions = AI_SYSTEM_INSTRUCTIONS.lower()

    assert "treat null values as unavailable data" in instructions
    assert 'treat "unknown" conditions as unknown' in instructions


def test_ai_instructions_prohibit_investment_recommendations():
    instructions = AI_SYSTEM_INSTRUCTIONS.lower()

    assert "buy, hold, sell" in instructions
    assert "do not" in instructions


def test_ai_instructions_define_narrative_output_fields():
    instructions = AI_SYSTEM_INSTRUCTIONS

    assert "summary" in instructions
    assert "quality_commentary" in instructions
    assert "risk_commentary" in instructions
    assert "valuation_commentary" in instructions
    assert "limitations" in instructions


def test_ai_prompt_is_valid():
    prompt = build_ai_prompt(_context())

    assert prompt.is_valid()


def test_ai_prompt_rejects_blank_instructions():
    prompt = AIPrompt(
        instructions=" ",
        context_json="{}",
    )

    assert not prompt.is_valid()


def test_ai_prompt_rejects_invalid_json():
    prompt = AIPrompt(
        instructions="Instructions",
        context_json="not-json",
    )

    assert not prompt.is_valid()


def test_ai_prompt_rejects_non_object_json():
    prompt = AIPrompt(
        instructions="Instructions",
        context_json="[]",
    )

    assert not prompt.is_valid()


def test_ai_prompt_is_frozen():
    prompt = build_ai_prompt(_context())

    with pytest.raises(FrozenInstanceError):
        prompt.context_json = "{}"
