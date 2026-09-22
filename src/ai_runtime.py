from src.config import Settings, settings
from src.providers.ai_base import AIProvider
from src.providers.ai_factory import build_ai_provider


def get_ai_provider(
    app_settings: Settings = settings,
) -> AIProvider:
    return build_ai_provider(
        app_settings.ai_provider
    )
