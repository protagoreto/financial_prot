from src.config import Settings, settings


def test_ai_provider_defaults_to_local():
    assert Settings().ai_provider == "local"


def test_global_settings_has_ai_provider():
    assert settings.ai_provider.strip()


def test_settings_accept_optional_telegram_configuration():
    app_settings = Settings(
        telegram_bot_token="test-token",
        telegram_chat_id="123456",
    )

    assert app_settings.telegram_bot_token == "test-token"
    assert app_settings.telegram_chat_id == "123456"


def test_settings_allows_missing_telegram_configuration():
    app_settings = Settings(
        telegram_bot_token=None,
        telegram_chat_id=None,
    )

    assert app_settings.telegram_bot_token is None
    assert app_settings.telegram_chat_id is None
