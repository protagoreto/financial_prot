import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.messaging import OutboundMessage
from src.providers.message_base import MessageProvider


TelegramTransport = Callable[
    [str, bytes, float],
    dict[str, object],
]


class TelegramMessageProvider(MessageProvider):
    def __init__(
        self,
        bot_token: str,
        timeout: float = 10.0,
        transport: TelegramTransport | None = None,
    ) -> None:
        normalized_token = bot_token.strip()

        if not normalized_token:
            raise ValueError(
                "Telegram bot token cannot be blank."
            )

        if timeout <= 0:
            raise ValueError(
                "Telegram timeout must be greater than zero."
            )

        self._bot_token = normalized_token
        self._timeout = timeout
        self._transport = (
            transport
            if transport is not None
            else _telegram_post_json
        )

    @property
    def name(self) -> str:
        return "telegram"

    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        if not message.is_valid():
            raise ValueError(
                "Outbound message is invalid."
            )

        if len(message.text) > 4096:
            raise ValueError(
                "Telegram message exceeds 4096 characters."
            )

        url = (
            "https://api.telegram.org/"
            f"bot{self._bot_token}/sendMessage"
        )

        payload = json.dumps(
            {
                "chat_id": message.destination,
                "text": message.text,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        response = self._transport(
            url,
            payload,
            self._timeout,
        )

        if response.get("ok") is not True:
            description = response.get(
                "description",
                "Telegram API request failed.",
            )

            raise RuntimeError(
                f"Telegram API error: {description}"
            )


def _telegram_post_json(
    url: str,
    payload: bytes,
    timeout: float,
) -> dict[str, object]:
    request = Request(
        url=url,
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw_response = response.read()
    except HTTPError as exc:
        raise RuntimeError(
            f"Telegram HTTP error: {exc.code}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            "Telegram network error."
        ) from exc

    try:
        decoded = json.loads(
            raw_response.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Telegram returned an invalid JSON response."
        ) from exc

    if not isinstance(decoded, dict):
        raise RuntimeError(
            "Telegram returned an invalid response."
        )

    return decoded
