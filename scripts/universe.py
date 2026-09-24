import argparse
from pathlib import Path

from src.config import settings
from src.db import connect, managed_connection
from src.universe_catalog import (
    load_universe_catalog,
    sync_universe_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load and synchronize a company universe catalog."
        )
    )

    parser.add_argument(
        "catalog",
        type=Path,
        help="CSV universe catalog.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help=(
            "Synchronize catalog companies into the database. "
            "Without this flag the command only validates and "
            "prints the universe."
        ),
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        companies = load_universe_catalog(
            args.catalog
        )

        print("=== UNIVERSE CATALOG ===")
        print(f"path: {args.catalog}")
        print(f"companies: {len(companies)}")

        profiles: dict[str, int] = {}

        for company in companies:
            profiles[company.fundamental_profile] = (
                profiles.get(
                    company.fundamental_profile,
                    0,
                )
                + 1
            )

            print(
                f"{company.ticker}/{company.exchange} "
                f"symbol={company.symbol} "
                f"currency={company.currency} "
                f"profile={company.fundamental_profile}"
            )

        print("profiles:")
        for profile in sorted(profiles):
            print(
                f"  {profile}: {profiles[profile]}"
            )

        if not args.sync:
            print("mode: validation_only")
            return 0

        with managed_connection(args.db_path) as connection:
            result = sync_universe_catalog(
                connection=connection,
                companies=companies,
            )

        print("mode: synchronized")
        print(f"created: {result.created}")
        print(f"existing: {result.existing}")
        print(f"total: {result.total}")

        return 0

    except ValueError as exc:
        parser.error(str(exc))

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
