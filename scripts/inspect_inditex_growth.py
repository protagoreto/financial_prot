from datetime import date

from src.config import settings
from src.db import connect, managed_connection
from src.fundamentals import (
    build_fundamental_growth_snapshot,
)


def get_inditex_company_id(connection) -> int:
    row = connection.execute(
        """
        SELECT company_id
        FROM companies
        WHERE ticker = ?
        """,
        ("ITX",),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Inditex (ITX) not found in database."
        )

    return row["company_id"]


def format_percentage(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return f"{value:.2%}"


def format_boolean(
    value: bool,
) -> str:
    return "YES" if value else "NO"


def main() -> None:
    dates = (
        date(2026, 3, 10),
        date(2026, 3, 11),
    )

    with managed_connection(settings.db_path) as connection:
        company_id = get_inditex_company_id(
            connection
        )

        print("INDITEX FUNDAMENTAL GROWTH")
        print("=" * 72)

        for as_of_date in dates:
            snapshot = (
                build_fundamental_growth_snapshot(
                    connection=connection,
                    company_id=company_id,
                    as_of_date=as_of_date,
                )
            )

            print()
            print(f"AS OF: {as_of_date}")
            print("-" * 72)

            if snapshot is None:
                print(
                    "No complete growth snapshot "
                    "available."
                )
                continue

            print(
                "Current period:     "
                f"{snapshot.current_period_end}"
            )
            print(
                "Previous period:    "
                f"{snapshot.previous_period_end}"
            )
            print(
                "Publication:        "
                f"{snapshot.current_publication_date}"
            )
            print(
                "Years between:      "
                f"{snapshot.years_between_periods:.4f}"
            )
            print(
                "Annual comparison:  "
                f"{format_boolean(snapshot.is_annual_comparison)}"
            )

            print()
            print("TOTAL PERIOD GROWTH")
            print("-" * 72)
            print(
                "Revenue growth:     "
                f"{format_percentage(snapshot.revenue_growth)}"
            )
            print(
                "EBITDA growth:      "
                f"{format_percentage(snapshot.ebitda_growth)}"
            )
            print(
                "EBIT growth:        "
                f"{format_percentage(snapshot.ebit_growth)}"
            )
            print(
                "Net income growth:  "
                f"{format_percentage(snapshot.net_income_growth)}"
            )
            print(
                "EPS growth:         "
                f"{format_percentage(snapshot.eps_growth)}"
            )
            print(
                "FCF growth:         "
                f"{format_percentage(snapshot.free_cash_flow_growth)}"
            )
            print(
                "Shares growth:      "
                f"{format_percentage(snapshot.shares_growth)}"
            )

            print()
            print("ANNUALIZED GROWTH (CAGR)")
            print("-" * 72)
            print(
                "Revenue CAGR:       "
                f"{format_percentage(snapshot.revenue_cagr)}"
            )
            print(
                "EBITDA CAGR:        "
                f"{format_percentage(snapshot.ebitda_cagr)}"
            )
            print(
                "EBIT CAGR:          "
                f"{format_percentage(snapshot.ebit_cagr)}"
            )
            print(
                "Net income CAGR:    "
                f"{format_percentage(snapshot.net_income_cagr)}"
            )
            print(
                "EPS CAGR:           "
                f"{format_percentage(snapshot.eps_cagr)}"
            )
            print(
                "FCF CAGR:           "
                f"{format_percentage(snapshot.free_cash_flow_cagr)}"
            )
            print(
                "Shares CAGR:        "
                f"{format_percentage(snapshot.shares_cagr)}"
            )

            print()
            print("QUALITY")
            print("-" * 72)
            print(
                "ROE:                "
                f"{format_percentage(snapshot.return_on_equity)}"
            )


if __name__ == "__main__":
    main()