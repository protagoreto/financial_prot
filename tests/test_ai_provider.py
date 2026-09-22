from src.ai import (
    AIAnalysisContext,
    AIAnalysisNarrative,
)
from src.providers.ai_base import AIProvider


class FakeAIProvider(AIProvider):
    @property
    def name(self) -> str:
        return "fake"

    def generate_analysis(
        self,
        context: AIAnalysisContext,
    ) -> AIAnalysisNarrative:
        return AIAnalysisNarrative(
            summary=f"Analysis for {context.name}.",
            quality_commentary="Quality context received.",
            risk_commentary="Risk context received.",
            valuation_commentary=(
                "Valuation context received."
            ),
            limitations=(
                "Generated only from supplied context.",
            ),
        )


def test_ai_provider_exposes_name():
    provider = FakeAIProvider()

    assert provider.name == "fake"


def test_ai_provider_generates_typed_narrative():
    from datetime import date

    from src.investment import AnalysisAvailability

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

    provider = FakeAIProvider()

    narrative = provider.generate_analysis(context)

    assert isinstance(
        narrative,
        AIAnalysisNarrative,
    )
    assert narrative.summary == (
        "Analysis for Test Company."
    )
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
