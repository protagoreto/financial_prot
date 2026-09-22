from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(
        os.getenv(
            "VIST_DB_PATH",
            "data/value_investing.sqlite",
        )
    )
    log_level: str = os.getenv(
        "LOG_LEVEL",
        "INFO",
    )
    ai_provider: str = os.getenv(
        "VIST_AI_PROVIDER",
        "local",
    )


settings = Settings()
