from pathlib import Path
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


def test_settings_reads_current_environment(monkeypatch):
    monkeypatch.setenv(
        "VIST_DB_PATH",
        "data/dynamic-test.sqlite",
    )
    monkeypatch.setenv(
        "LOG_LEVEL",
        "DEBUG",
    )
    monkeypatch.setenv(
        "VIST_AI_PROVIDER",
        "dynamic-provider",
    )
    monkeypatch.setenv(
        "VIST_TELEGRAM_BOT_TOKEN",
        "dynamic-token",
    )
    monkeypatch.setenv(
        "VIST_TELEGRAM_CHAT_ID",
        "dynamic-chat",
    )

    app_settings = Settings()

    assert app_settings.db_path == Path(
        "data/dynamic-test.sqlite"
    )
    assert app_settings.log_level == "DEBUG"
    assert app_settings.ai_provider == "dynamic-provider"
    assert app_settings.telegram_bot_token == "dynamic-token"
    assert app_settings.telegram_chat_id == "dynamic-chat"


def test_settings_reads_environment_for_each_instance(
    monkeypatch,
):
    monkeypatch.setenv(
        "VIST_AI_PROVIDER",
        "first-provider",
    )

    first = Settings()

    monkeypatch.setenv(
        "VIST_AI_PROVIDER",
        "second-provider",
    )

    second = Settings()

    assert first.ai_provider == "first-provider"
    assert second.ai_provider == "second-provider"
