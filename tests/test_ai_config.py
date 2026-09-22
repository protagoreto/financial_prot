from src.config import Settings, settings


def test_ai_provider_defaults_to_local():
    assert Settings().ai_provider == "local"


def test_global_settings_has_ai_provider():
    assert settings.ai_provider.strip()
