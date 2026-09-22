import json
from datetime import date

import pytest

from src.ai import AIAnalysisNarrative
from src.ai_prompt import AIPrompt, AI_SYSTEM_INSTRUCTIONS
from src.ai_service import (
    AIAnalysisResult,
    generate_ai_analysis,
)
from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.providers.ai_base import AIProvider
from src.radar import RadarEntry, RadarScenario
from src.value import ValueCondition


def _entry() -> RadarEntry:
    return RadarEntry(
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
            RadarScenario(
                name="Base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
        ),
    )


class ValidProvider(AIProvider):
    def __init__(self) -> None:
        self.received_prompt: AIPrompt | None = None

    @property
    def name(self) -> str:
        return "valid"

    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        self.received_prompt = prompt

        context = json.loads(prompt.context_json)

        return AIAnalysisNarrative(
            summary=(
                f"Analysis for "
                f"{context['company']['name']}."
            ),
            quality_commentary=(
                "Quality assessment interpreted."
            ),
            risk_commentary=(
                "Risk assessment interpreted."
            ),
            valuation_commentary=(
                "Valuation scenarios interpreted."
            ),
            limitations=(
                "Uses only supplied deterministic prompt.",
            ),
        )


class BlankNameProvider(ValidProvider):
    @property
    def name(self) -> str:
        return " "


class InvalidNarrativeProvider(ValidProvider):
    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        self.received_prompt = prompt

        return AIAnalysisNarrative(
            summary="",
            quality_commentary="Quality commentary.",
            risk_commentary="Risk commentary.",
            valuation_commentary="Valuation commentary.",
            limitations=(),
        )


class WrongTypeProvider(ValidProvider):
    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        self.received_prompt = prompt

        return "not a narrative"  # type: ignore[return-value]


class FailingProvider(ValidProvider):
    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        self.received_prompt = prompt
        raise RuntimeError("provider unavailable")


def test_generate_ai_analysis_returns_typed_result():
    result = generate_ai_analysis(
        provider=ValidProvider(),
        entry=_entry(),
    )

    assert isinstance(result, AIAnalysisResult)
    assert result.provider_name == "valid"
    assert result.context.company_id == 1
    assert result.context.name == "Test Company"
    assert result.prompt.is_valid()
    assert isinstance(
        result.narrative,
        AIAnalysisNarrative,
    )
    assert result.narrative.is_valid()


def test_generate_ai_analysis_preserves_deterministic_context():
    entry = _entry()

    result = generate_ai_analysis(
        provider=ValidProvider(),
        entry=entry,
    )

    assert result.context.as_of_date == entry.as_of_date
    assert (
        result.context.fiscal_period_end
        == entry.fiscal_period_end
    )
    assert (
        result.context.quality_level
        == entry.quality_level
    )
    assert result.context.risk_level == entry.risk_level
    assert (
        result.context.value_trap_warning
        == entry.value_trap_warning
    )

    assert result.context.scenarios[0].expected_return == 0.12
    assert result.context.scenarios[0].required_price == 55.0
    assert result.context.scenarios[0].price_margin == 0.10
    assert (
        result.context.scenarios[0].condition
        == ValueCondition.TARGET_MET
    )


def test_generate_ai_analysis_passes_prepared_prompt_to_provider():
    provider = ValidProvider()

    result = generate_ai_analysis(
        provider=provider,
        entry=_entry(),
    )

    assert provider.received_prompt == result.prompt
    assert (
        result.prompt.instructions
        == AI_SYSTEM_INSTRUCTIONS
    )

    decoded = json.loads(result.prompt.context_json)

    assert decoded["company"]["company_id"] == 1
    assert decoded["company"]["name"] == "Test Company"

    scenario = decoded["analysis"]["scenarios"][0]

    assert scenario["expected_return"] == 0.12
    assert scenario["required_price"] == 55.0
    assert scenario["price_margin"] == 0.10
    assert scenario["condition"] == "target_met"


def test_generate_ai_analysis_rejects_blank_provider_name():
    with pytest.raises(
        ValueError,
        match="AI provider name cannot be blank",
    ):
        generate_ai_analysis(
            provider=BlankNameProvider(),
            entry=_entry(),
        )


def test_generate_ai_analysis_rejects_invalid_narrative():
    with pytest.raises(
        ValueError,
        match="invalid narrative",
    ):
        generate_ai_analysis(
            provider=InvalidNarrativeProvider(),
            entry=_entry(),
        )


def test_generate_ai_analysis_rejects_wrong_return_type():
    with pytest.raises(
        TypeError,
        match="must return AIAnalysisNarrative",
    ):
        generate_ai_analysis(
            provider=WrongTypeProvider(),
            entry=_entry(),
        )


def test_generate_ai_analysis_propagates_provider_failure():
    provider = FailingProvider()

    with pytest.raises(
        RuntimeError,
        match="provider unavailable",
    ):
        generate_ai_analysis(
            provider=provider,
            entry=_entry(),
        )

    assert provider.received_prompt is not None
    assert provider.received_prompt.is_valid()


def test_ai_analysis_result_is_frozen():
    result = generate_ai_analysis(
        provider=ValidProvider(),
        entry=_entry(),
    )

    with pytest.raises(AttributeError):
        result.provider_name = "changed"
