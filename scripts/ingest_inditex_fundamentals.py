from src.config import settings
from src.db import connect, initialize_database
from src.ingestion import (
    get_or_create_company,
    ingest_financials,
)
from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)


def main() -> None:
    initialize_database(settings.db_path)

    provider = YahooFundamentalsProvider()

    with connect(settings.db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Industria de Diseño Textil, S.A.",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        count = ingest_financials(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="ITX.MC",
            currency="EUR",
        )

        rows = connection.execute(
            """
            SELECT
                f.period_end,
                f.statement_type,
                f.metric,
                f.value,
                f.currency,
                f.publication_date,
                s.provider,
                s.retrieved_at
            FROM financials AS f
            JOIN sources AS s
                ON s.source_id = f.source_id
            WHERE f.company_id = ?
            ORDER BY
                f.period_end DESC,
                f.statement_type,
                f.metric
            """,
            (company_id,),
        ).fetchall()

    print()
    print("INDITEX FUNDAMENTALS INGESTION")
    print("=" * 90)
    print(f"Processed records: {count}")
    print(f"Stored records:    {len(rows)}")
    print()

    for row in rows:
        print(
            f"{row['period_end']} | "
            f"{row['metric']:<22} | "
            f"{row['value']:>18,.2f} | "
            f"{row['currency']} | "
            f"publication={row['publication_date']} | "
            f"source={row['provider']}"
        )


if __name__ == "__main__":
    main()