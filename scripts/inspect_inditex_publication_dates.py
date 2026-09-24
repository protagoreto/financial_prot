from src.config import settings
from src.db import connect, managed_connection


def main() -> None:
    with managed_connection(settings.db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                pd.period_end,
                pd.period_type,
                pd.publication_date,
                s.provider,
                s.document_type,
                s.confidence,
                s.url
            FROM publication_dates AS pd
            JOIN companies AS c
                ON c.company_id = pd.company_id
            JOIN sources AS s
                ON s.source_id = pd.source_id
            WHERE c.ticker = ?
            AND c.exchange = ?
            ORDER BY pd.period_end
            """,
            (
                "ITX",
                "BME",
            ),
        ).fetchall()

    print()
    print("INDITEX PUBLICATION DATES")
    print("=" * 80)

    for row in rows:
        print(
            f"{row['period_end']} | "
            f"{row['period_type']} | "
            f"{row['publication_date']} | "
            f"{row['provider']} | "
            f"{row['document_type']} | "
            f"{row['confidence']} | "
            f"url={row['url']}"
        )

    print()
    print(f"Total: {len(rows)}")


if __name__ == "__main__":
    main()