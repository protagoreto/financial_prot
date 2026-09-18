import logging
from src.config import settings
from src.db import initialize_database
from src.logging_config import configure_logging

def run() -> None:
    configure_logging(settings.log_level)
    initialize_database(settings.db_path)
    logging.getLogger(__name__).info(
        "Daily pipeline bootstrap completed: %s", settings.db_path
    )

if __name__ == "__main__":
    run()
