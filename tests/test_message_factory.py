import pytest

from src.providers.message_base import MessageProvider
from src.providers.message_factory import build_message_provider
from src.providers.telegram import TelegramMessageProvider


def test_build_telegram_message_provider():
    provider = build_message_provider(
        provider_name=" telegram ",
        telegram_bot_token="test-token",
    )

    assert isinstance(provider, MessageProvider)
    assert isinstance(provider, TelegramMessageProvider)
    assert provider.name == "telegram"


def test_build_telegram_message_provider_requires_token():
    with pytest.raises(
        ValueError,
        match="Telegram bot token is required",
    ):
        build_message_provider(
            provider_name="telegram",
            telegram_bot_token=None,
        )


def test_build_message_provider_rejects_unsupported_provider():
    with pytest.raises(
        ValueError,
        match="Unsupported message provider",
    ):
        build_message_provider(
            provider_name="unsupported",
        )
