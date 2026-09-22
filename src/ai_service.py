from dataclasses import dataclass

from src.ai import (
    AIAnalysisContext,
    AIAnalysisNarrative,
    build_ai_analysis_context,
)
from src.providers.ai_base import AIProvider
from src.radar import RadarEntry


@dataclass(frozen=True)
class AIAnalysisResult:
    provider_name: str
    context: AIAnalysisContext
    narrative: AIAnalysisNarrative


def generate_ai_analysis(
    provider: AIProvider,
    entry: RadarEntry,
) -> AIAnalysisResult:
    provider_name = provider.name.strip()

    if not provider_name:
        raise ValueError(
            "AI provider name cannot be blank."
        )

    context = build_ai_analysis_context(entry)

    narrative = provider.generate_analysis(context)

    if not isinstance(
        narrative,
        AIAnalysisNarrative,
    ):
        raise TypeError(
            "AI provider must return AIAnalysisNarrative."
        )

    if not narrative.is_valid():
        raise ValueError(
            "AI provider returned an invalid narrative."
        )

    return AIAnalysisResult(
        provider_name=provider_name,
        context=context,
        narrative=narrative,
    )
