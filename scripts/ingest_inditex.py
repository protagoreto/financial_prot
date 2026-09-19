from datetime import date

from src.config import settings
from src.db import connect, initialize_database
from src.ingestion import get_or_create_company, ingest_prices
from src.providers.yahoo import YahooPriceProvider


def main() -> None:
    initialize_database(settings.db_path)

    provider = YahooPriceProvider()

    with connect(settings.db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Industria de Diseño Textil, S.A.",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        count = ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
            start_date=date(2026, 9, 14),
            end_date=date(2026, 9, 18),
        )

    print(
        f"Inditex ingestion completed: "
        f"{count} price records processed."
    )


if __name__ == "__main__":
    main()