import argparse
from pathlib import Path

from src.company_discovery import (
    discover_companies,
    register_company_candidate,
)
from src.config import settings
from src.db import connect, managed_connection
from src.providers.yahoo_discovery import (
    YahooCompanyDiscoveryProvider,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover equity symbols and optionally "
            "register one company."
        )
    )

    parser.add_argument(
        "query",
        help="Company name or ticker to search.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--select",
        type=int,
        help=(
            "1-based result number to register. "
            "Omit for read-only discovery."
        ),
    )
    parser.add_argument(
        "--exchange",
        help=(
            "Internal exchange identity for registration, "
            "for example BME or NASDAQ."
        ),
    )
    parser.add_argument(
        "--fundamental-profile",
        choices=("operating", "financial"),
        help=(
            "Explicit fundamental model for registration."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
    )

    return parser


def _display(value: str | None) -> str:
    return value if value is not None else "unknown"


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_results <= 0:
        parser.error("--max-results must be positive.")

    provider = YahooCompanyDiscoveryProvider()

    try:
        candidates = discover_companies(
            provider=provider,
            query=args.query,
            max_results=args.max_results,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print("=== COMPANY DISCOVERY ===")
    print(f"provider: {provider.name}")
    print(f"query: {args.query}")
    print(f"equity_candidates: {len(candidates)}")

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print(
            f"{index}. {candidate.symbol} | "
            f"{candidate.name} | "
            f"provider_exchange="
            f"{_display(candidate.provider_exchange)} | "
            f"market="
            f"{_display(candidate.exchange_display)}"
        )

    if args.select is None:
        print("mode: discovery_only")
        return 0

    if not candidates:
        parser.error(
            "No equity candidates available for selection."
        )

    if (
        args.select < 1
        or args.select > len(candidates)
    ):
        parser.error(
            "--select is outside the result range."
        )

    if args.exchange is None:
        parser.error(
            "--exchange is required with --select."
        )

    if args.fundamental_profile is None:
        parser.error(
            "--fundamental-profile is required "
            "with --select."
        )

    selected = candidates[args.select - 1]

    try:
        enriched = provider.enrich(selected)
    except ValueError as exc:
        parser.error(str(exc))

    print("selected:")
    print(f"  symbol: {enriched.symbol}")
    print(f"  name: {enriched.name}")
    print(
        f"  provider_exchange: "
        f"{_display(enriched.provider_exchange)}"
    )
    print(
        f"  currency: {_display(enriched.currency)}"
    )
    print(
        f"  country: {_display(enriched.country)}"
    )
    print(
        f"  sector: {_display(enriched.sector)}"
    )
    print(
        f"  industry: {_display(enriched.industry)}"
    )

    try:
        with managed_connection(args.db_path) as connection:
            company_id, company = (
                register_company_candidate(
                    connection=connection,
                    candidate=enriched,
                    exchange=args.exchange,
                    fundamental_profile=(
                        args.fundamental_profile
                    ),
                )
            )
    except ValueError as exc:
        parser.error(str(exc))

    print("mode: registered")
    print(f"company_id: {company_id}")
    print(f"ticker: {company.ticker}")
    print(f"symbol: {company.symbol}")
    print(f"exchange: {company.exchange}")
    print(
        "fundamental_profile: "
        f"{company.fundamental_profile}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
