import pytest

from src.config import Settings
from src.message_runtime import MessageRuntime, get_message_runtime
from src.providers.telegram import TelegramMessageProvider


def _settings(
    telegram_bot_token: str | None = "test-token",
    telegram_chat_id: str | None = "123456",
) -> Settings:
    return Settings(
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )


def test_get_telegram_message_runtime():
    runtime = get_message_runtime(
        provider_name=" telegram ",
        app_settings=_settings(),
    )

    assert isinstance(runtime, MessageRuntime)
    assert isinstance(
        runtime.provider,
        TelegramMessageProvider,
    )
    assert runtime.provider.name == "telegram"
    assert runtime.destination == "123456"


def test_get_telegram_message_runtime_strips_destination():
    runtime = get_message_runtime(
        provider_name="telegram",
        app_settings=_settings(
            telegram_chat_id=" 123456 ",
        ),
    )

    assert runtime.destination == "123456"


def test_get_telegram_message_runtime_requires_chat_id():
    with pytest.raises(
        ValueError,
        match="Telegram chat ID is required",
    ):
        get_message_runtime(
            provider_name="telegram",
            app_settings=_settings(
                telegram_chat_id=None,
            ),
        )


def test_get_telegram_message_runtime_rejects_blank_chat_id():
    with pytest.raises(
        ValueError,
        match="Telegram chat ID is required",
    ):
        get_message_runtime(
            provider_name="telegram",
            app_settings=_settings(
                telegram_chat_id=" ",
            ),
        )


def test_get_telegram_message_runtime_requires_token():
    with pytest.raises(
        ValueError,
        match="Telegram bot token is required",
    ):
        get_message_runtime(
            provider_name="telegram",
            app_settings=_settings(
                telegram_bot_token=None,
            ),
        )


def test_get_message_runtime_rejects_unsupported_provider():
    with pytest.raises(
        ValueError,
        match="Unsupported message provider",
    ):
        get_message_runtime(
            provider_name="unsupported",
            app_settings=_settings(),
        )
