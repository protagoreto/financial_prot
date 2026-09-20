from datetime import date

from src.config import settings
from src.db import connect
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_latest_financial_on_or_before,
)


DATES = [
    date(2026, 3, 10),
    date(2026, 3, 11),
]


def main() -> None:
    with connect(settings.db_path) as connection:
        company = connection.execute(
            """
            SELECT company_id
            FROM companies
            WHERE ticker = ?
            AND exchange = ?
            """,
            (
                "ITX",
                "BME",
            ),
        ).fetchone()

        if company is None:
            raise RuntimeError(
                "Inditex is not present in the database."
            )

        company_id = company["company_id"]

        print()
        print("INDITEX POINT-IN-TIME EPS")
        print("=" * 80)

        for as_of_date in DATES:
            record = get_latest_financial_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                as_of_date=as_of_date,
                period_type=PeriodType.ANNUAL,
            )

            if record is None:
                print(
                    f"{as_of_date} | "
                    "EPS unavailable"
                )
                continue

            print(
                f"{as_of_date} | "
                f"period_end={record.period_end} | "
                f"publication={record.publication_date} | "
                f"EPS={record.value:.3f}"
            )


if __name__ == "__main__":
    main()