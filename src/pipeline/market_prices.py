from datetime import date

from src.config import settings
from src.db import connect, managed_connection, initialize_database
from src.ingestion import (
    get_or_create_company,
    ingest_prices_incremental,
)
from src.providers.yahoo import YahooPriceProvider
from src.universe import IBEX_UNIVERSE


INITIAL_START_DATE = date(2020, 1, 1)


def run(
    end_date: date | None = None,
) -> dict[str, int]:
    initialize_database(settings.db_path)

    if end_date is None:
        end_date = date.today()

    provider = YahooPriceProvider()
    results: dict[str, int] = {}

    with managed_connection(settings.db_path) as connection:
        for company in IBEX_UNIVERSE:
            company_id = get_or_create_company(
                connection=connection,
                name=company.name,
                ticker=company.ticker,
                exchange=company.exchange,
                currency=company.currency,
                fundamental_profile=(
                    company.fundamental_profile
                ),
            )

            count = ingest_prices_incremental(
                connection=connection,
                provider=provider,
                company_id=company_id,
                symbol=company.symbol,
                currency=company.currency,
                initial_start_date=INITIAL_START_DATE,
                end_date=end_date,
            )

            results[company.ticker] = count

    return results


def main() -> None:
    results = run()

    print("Market price ingestion completed.")

    for ticker, count in results.items():
        print(
            f"{ticker}: {count} price records processed."
        )


if __name__ == "__main__":
    main()