from src.providers.message_base import MessageProvider
from src.providers.telegram import TelegramMessageProvider


def build_message_provider(
    provider_name: str,
    telegram_bot_token: str | None = None,
) -> MessageProvider:
    normalized_name = provider_name.strip().lower()

    if normalized_name == "telegram":
        if telegram_bot_token is None:
            raise ValueError(
                "Telegram bot token is required."
            )

        return TelegramMessageProvider(
            bot_token=telegram_bot_token,
        )

    raise ValueError(
        f"Unsupported message provider: {provider_name!r}"
    )
