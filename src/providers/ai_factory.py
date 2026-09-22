from src.providers.ai_base import AIProvider
from src.providers.ai_local import LocalAIProvider


def build_ai_provider(
    provider_name: str,
) -> AIProvider:
    normalized_name = provider_name.strip().lower()

    if normalized_name == "local":
        return LocalAIProvider()

    raise ValueError(
        f"Unsupported AI provider: {provider_name!r}"
    )
