import argparse
from datetime import date
from pathlib import Path

from src.config import settings
from src.db import connect, managed_connection
from src.onboarding import onboard_company
from src.providers.sec_publication_dates import (
    SecPublicationDateProvider,
)
from src.providers.yahoo import YahooPriceProvider
from src.providers.yahoo_dividends import YahooDividendProvider
from src.providers.yahoo_estimates import YahooEstimateProvider
from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)
from src.repository import (
    get_company_id_by_ticker_exchange,
)


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid ISO date: {value}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Onboard a registered company using its "
            "persisted provider symbol."
        )
    )

    identity = parser.add_mutually_exclusive_group(
        required=True
    )

    identity.add_argument(
        "--company-id",
        type=int,
        help="Registered company ID.",
    )
    identity.add_argument(
        "--ticker",
        help=(
            "Registered ticker. Requires --exchange."
        ),
    )

    parser.add_argument(
        "--exchange",
        help=(
            "Internal exchange identity when using --ticker."
        ),
    )
    parser.add_argument(
        "--initial-price-date",
        type=_date_value,
        required=True,
        help="Initial price history date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=_date_value,
        default=date.today(),
        help=(
            "Final price date (YYYY-MM-DD). "
            "Defaults to today."
        ),
    )
    parser.add_argument(
        "--estimate-date",
        type=_date_value,
        help=(
            "Estimate observation date (YYYY-MM-DD). "
            "Defaults to provider observation time."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
        help="SQLite database path.",
    )

    return parser


def _resolve_company_id(
    parser: argparse.ArgumentParser,
    args,
    connection,
) -> int:
    if args.company_id is not None:
        if args.exchange is not None:
            parser.error(
                "--exchange cannot be used with --company-id."
            )

        return args.company_id

    if args.exchange is None:
        parser.error(
            "--exchange is required with --ticker."
        )

    company_id = get_company_id_by_ticker_exchange(
        connection=connection,
        ticker=args.ticker,
        exchange=args.exchange,
    )

    if company_id is None:
        parser.error(
            "Registered company not found for "
            f"{args.ticker}/{args.exchange}."
        )

    return company_id


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.initial_price_date > args.end_date:
        parser.error(
            "--initial-price-date cannot be after --end-date."
        )

    with managed_connection(args.db_path) as connection:
        company_id = _resolve_company_id(
            parser,
            args,
            connection,
        )

        publication_date_provider = (
            SecPublicationDateProvider(settings.sec_user_agent)
            if settings.sec_user_agent
            else None
        )

        try:
            result = onboard_company(
                connection=connection,
                company_id=company_id,
                price_provider=YahooPriceProvider(),
                fundamentals_provider=(
                    YahooFundamentalsProvider()
                ),
                estimate_provider=YahooEstimateProvider(),
                dividend_provider=YahooDividendProvider(),
                initial_price_date=args.initial_price_date,
                end_date=args.end_date,
                estimate_date=args.estimate_date,
                publication_date_provider=(
                    publication_date_provider
                ),
            )
        except ValueError as exc:
            parser.error(str(exc))

    print("=== COMPANY ONBOARDING ===")
    print(f"company_id: {result.company_id}")
    print(f"symbol: {result.symbol}")

    for step in result.steps:
        line = (
            f"{step.name}: {step.status.value}"
        )

        if step.processed is not None:
            line += f" processed={step.processed}"

        if step.detail is not None:
            line += f" detail={step.detail}"

        print(line)

    print("summary:")
    print(f"  success: {result.succeeded}")
    print(f"  unavailable: {result.unavailable}")
    print(f"  failed: {result.failed}")

    print(
        "point_in_time_note: annual fundamentals "
        "without verified publication dates remain "
        "unavailable to PIT analysis."
    )

    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
