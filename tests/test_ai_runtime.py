import pytest

from src.ai_runtime import get_ai_provider
from src.config import Settings
from src.providers.ai_local import LocalAIProvider


def test_get_ai_provider_uses_settings():
    app_settings = Settings(
        ai_provider="local",
    )

    provider = get_ai_provider(app_settings)

    assert isinstance(provider, LocalAIProvider)
    assert provider.name == "local"


def test_get_ai_provider_rejects_unsupported_setting():
    app_settings = Settings(
        ai_provider="unsupported",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported AI provider",
    ):
        get_ai_provider(app_settings)
