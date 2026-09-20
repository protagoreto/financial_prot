from datetime import date

from src.config import settings
from src.db import connect, initialize_database
from src.ingestion import (
    create_source,
    get_or_create_company,
)
from src.metrics import PeriodType
from src.repository import (
    get_verified_publication_date,
    insert_publication_date,
)


PUBLICATION_DATES = [
    (
        date(2023, 1, 31),
        date(2023, 3, 15),
    ),
    (
        date(2024, 1, 31),
        date(2024, 3, 13),
    ),
    (
        date(2025, 1, 31),
        date(2025, 3, 12),
    ),
    (
        date(2026, 1, 31),
        date(2026, 3, 11),
    ),
]


def main() -> None:
    initialize_database(settings.db_path)

    with connect(settings.db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Industria de Diseño Textil, S.A.",
            ticker="ITX",
            exchange="BME",
            currency="EUR",
        )

        for period_end, publication_date in PUBLICATION_DATES:
            existing_date = get_verified_publication_date(
                connection=connection,
                company_id=company_id,
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
            )

            if existing_date == publication_date:
                print(
                    f"{period_end} -> "
                    f"{publication_date} "
                    f"(already stored)"
                )
                continue

            source_id = create_source(
                connection=connection,
                provider="inditex",
                document_type="annual_results",
                publication_date=publication_date,
                confidence="primary",
            )

            insert_publication_date(
                connection=connection,
                company_id=company_id,
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
                source_id=source_id,
            )

            print(
                f"{period_end} -> "
                f"{publication_date}"
            )


if __name__ == "__main__":
    main()