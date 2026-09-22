import json
from datetime import date

from src.ai import (
    AIAnalysisContext,
    AIAnalysisNarrative,
)
from src.ai_prompt import AIPrompt, build_ai_prompt
from src.investment import AnalysisAvailability
from src.providers.ai_base import AIProvider


class FakeAIProvider(AIProvider):
    @property
    def name(self) -> str:
        return "fake"

    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        context = json.loads(prompt.context_json)

        return AIAnalysisNarrative(
            summary=(
                f"Analysis for "
                f"{context['company']['name']}."
            ),
            quality_commentary="Quality context received.",
            risk_commentary="Risk context received.",
            valuation_commentary=(
                "Valuation context received."
            ),
            limitations=(
                "Generated only from supplied prompt.",
            ),
        )


def _prompt() -> AIPrompt:
    context = AIAnalysisContext(
        company_id=1,
        name="Test Company",
        ticker="TEST",
        exchange="BME",
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

    return build_ai_prompt(context)


def test_ai_provider_exposes_name():
    provider = FakeAIProvider()

    assert provider.name == "fake"


def test_ai_provider_generates_typed_narrative():
    provider = FakeAIProvider()

    narrative = provider.generate_analysis(_prompt())

    assert isinstance(
        narrative,
        AIAnalysisNarrative,
    )
    assert narrative.summary == (
        "Analysis for Test Company."
    )
    assert narrative.is_valid()


def test_ai_provider_receives_prepared_prompt():
    provider = FakeAIProvider()
    prompt = _prompt()

    narrative = provider.generate_analysis(prompt)

    assert prompt.is_valid()
    assert prompt.instructions.strip()
    assert narrative.is_valid()


def test_ai_provider_is_abstract():
    try:
        AIProvider()
    except TypeError:
        pass
    else:
        raise AssertionError(
            "AIProvider must remain abstract."
        )
