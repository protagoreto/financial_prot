import json

import pytest

from src.messaging import OutboundMessage
from src.providers.message_base import MessageProvider
from src.providers.telegram import TelegramMessageProvider


class FakeTelegramTransport:
    def __init__(
        self,
        response: dict[str, object] | None = None,
    ) -> None:
        self.response = (
            {"ok": True}
            if response is None
            else response
        )
        self.calls: list[
            tuple[str, bytes, float]
        ] = []

    def __call__(
        self,
        url: str,
        payload: bytes,
        timeout: float,
    ) -> dict[str, object]:
        self.calls.append(
            (url, payload, timeout)
        )
        return self.response


def test_telegram_provider_implements_message_provider():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    assert isinstance(provider, MessageProvider)
    assert provider.name == "telegram"


def test_telegram_provider_sends_expected_request():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        timeout=5.0,
        transport=transport,
    )

    message = OutboundMessage(
        destination="123456",
        text="Test message",
    )

    provider.send(message)

    assert len(transport.calls) == 1

    url, payload, timeout = transport.calls[0]

    assert url == (
        "https://api.telegram.org/"
        "bottest-token/sendMessage"
    )
    assert timeout == 5.0

    decoded = json.loads(
        payload.decode("utf-8")
    )

    assert decoded == {
        "chat_id": "123456",
        "text": "Test message",
    }


def test_telegram_provider_preserves_unicode():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    provider.send(
        OutboundMessage(
            destination="123456",
            text="AnÃ¡lisis vÃ¡lido",
        )
    )

    _, payload, _ = transport.calls[0]

    decoded = json.loads(
        payload.decode("utf-8")
    )

    assert decoded["text"] == "AnÃ¡lisis vÃ¡lido"


def test_telegram_provider_rejects_blank_token():
    with pytest.raises(
        ValueError,
        match="Telegram bot token cannot be blank",
    ):
        TelegramMessageProvider(
            bot_token=" ",
        )


def test_telegram_provider_rejects_invalid_timeout():
    with pytest.raises(
        ValueError,
        match="Telegram timeout must be greater than zero",
    ):
        TelegramMessageProvider(
            bot_token="test-token",
            timeout=0,
        )


def test_telegram_provider_rejects_invalid_message():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    with pytest.raises(
        ValueError,
        match="Outbound message is invalid",
    ):
        provider.send(
            OutboundMessage(
                destination=" ",
                text="Test message",
            )
        )

    assert transport.calls == []


def test_telegram_provider_rejects_message_over_limit():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    with pytest.raises(
        ValueError,
        match="exceeds 4096 characters",
    ):
        provider.send(
            OutboundMessage(
                destination="123456",
                text="x" * 4097,
            )
        )

    assert transport.calls == []


def test_telegram_provider_accepts_message_at_limit():
    transport = FakeTelegramTransport()

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    provider.send(
        OutboundMessage(
            destination="123456",
            text="x" * 4096,
        )
    )

    assert len(transport.calls) == 1


def test_telegram_provider_raises_api_error():
    transport = FakeTelegramTransport(
        response={
            "ok": False,
            "description": "Bad Request",
        }
    )

    provider = TelegramMessageProvider(
        bot_token="test-token",
        transport=transport,
    )

    with pytest.raises(
        RuntimeError,
        match="Telegram API error: Bad Request",
    ):
        provider.send(
            OutboundMessage(
                destination="123456",
                text="Test message",
            )
        )
