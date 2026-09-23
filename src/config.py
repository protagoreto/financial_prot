from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


def _env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


def _env_string(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_optional_string(name: str) -> str | None:
    return os.getenv(name)


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(
        default_factory=lambda: _env_path(
            "VIST_DB_PATH",
            "data/value_investing.sqlite",
        )
    )
    log_level: str = field(
        default_factory=lambda: _env_string(
            "LOG_LEVEL",
            "INFO",
        )
    )
    ai_provider: str = field(
        default_factory=lambda: _env_string(
            "VIST_AI_PROVIDER",
            "local",
        )
    )
    telegram_bot_token: str | None = field(
        default_factory=lambda: _env_optional_string(
            "VIST_TELEGRAM_BOT_TOKEN"
        )
    )
    telegram_chat_id: str | None = field(
        default_factory=lambda: _env_optional_string(
            "VIST_TELEGRAM_CHAT_ID"
        )
    )


settings = Settings()
