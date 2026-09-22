from dataclasses import dataclass

from src.config import Settings, settings
from src.providers.message_base import MessageProvider
from src.providers.message_factory import build_message_provider


@dataclass(frozen=True)
class MessageRuntime:
    provider: MessageProvider
    destination: str


def get_message_runtime(
    provider_name: str,
    app_settings: Settings = settings,
) -> MessageRuntime:
    normalized_provider_name = provider_name.strip().lower()

    if normalized_provider_name == "telegram":
        destination = app_settings.telegram_chat_id

        if destination is None or not destination.strip():
            raise ValueError(
                "Telegram chat ID is required."
            )

        provider = build_message_provider(
            provider_name=normalized_provider_name,
            telegram_bot_token=app_settings.telegram_bot_token,
        )

        return MessageRuntime(
            provider=provider,
            destination=destination.strip(),
        )

    raise ValueError(
        f"Unsupported message provider: {provider_name!r}"
    )
