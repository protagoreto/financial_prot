import argparse
from datetime import date
from pathlib import Path

from src.application_flow import (
    describe_analysis_state,
    run_application_flow,
)
from src.company_discovery import discover_companies
from src.config import settings
from src.db import connect
from src.providers.yahoo import YahooPriceProvider
from src.providers.yahoo_discovery import (
    YahooCompanyDiscoveryProvider,
)
from src.providers.yahoo_dividends import YahooDividendProvider
from src.providers.yahoo_estimates import YahooEstimateProvider
from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)
from src.scenarios import ValuationScenario


DEFAULT_SCENARIOS = (
    ValuationScenario(
        name="conservative",
        eps_growth=0.02,
        dividend_yield=0.02,
        terminal_pe=10.0,
    ),
    ValuationScenario(
        name="base",
        eps_growth=0.06,
        dividend_yield=0.03,
        terminal_pe=14.0,
    ),
    ValuationScenario(
        name="optimistic",
        eps_growth=0.10,
        dividend_yield=0.04,
        terminal_pe=18.0,
    ),
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
            "Discover and optionally onboard and analyze "
            "one company."
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
        help="Maximum discovery results.",
    )
    parser.add_argument(
        "--select",
        type=int,
        help=(
            "1-based discovery result to register and process. "
            "Omit for discovery only."
        ),
    )
    parser.add_argument(
        "--exchange",
        help=(
            "Internal exchange identity. Required with --select."
        ),
    )
    parser.add_argument(
        "--fundamental-profile",
        choices=("operating", "financial"),
        help=(
            "Fundamental model. Required with --select."
        ),
    )
    parser.add_argument(
        "--initial-price-date",
        type=_date_value,
        help=(
            "Initial price date. Required with --select."
        ),
    )
    parser.add_argument(
        "--end-date",
        type=_date_value,
        default=date.today(),
        help="Final ingestion date. Defaults to today.",
    )
    parser.add_argument(
        "--as-of-date",
        type=_date_value,
        help=(
            "Point-in-time analysis date. Defaults to --end-date."
        ),
    )
    parser.add_argument(
        "--estimate-date",
        type=_date_value,
        help="Optional estimate observation date.",
    )
    parser.add_argument(
        "--target-return",
        type=float,
        default=0.10,
        help="Annual target return as a decimal.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Valuation horizon in years.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
        help="SQLite database path.",
    )

    return parser


def _validate_selected_args(
    parser: argparse.ArgumentParser,
    args,
) -> None:
    if args.select is None:
        selected_only = (
            args.exchange,
            args.fundamental_profile,
            args.initial_price_date,
            args.as_of_date,
            args.estimate_date,
        )

        if any(value is not None for value in selected_only):
            parser.error(
                "Processing options require --select."
            )

        return

    if args.select <= 0:
        parser.error("--select must be greater than zero.")

    if args.exchange is None:
        parser.error("--exchange is required with --select.")

    if args.fundamental_profile is None:
        parser.error(
            "--fundamental-profile is required with --select."
        )

    if args.initial_price_date is None:
        parser.error(
            "--initial-price-date is required with --select."
        )


def _print_candidates(candidates) -> None:
    print("=== COMPANY DISCOVERY ===")

    if not candidates:
        print("no_results")
        return

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index}. "
            f"symbol={candidate.symbol} "
            f"name={candidate.name} "
            f"currency={candidate.currency or 'n/a'} "
            f"provider_exchange="
            f"{candidate.provider_exchange or 'n/a'}"
        )


def _print_result(result) -> None:
    coverage = result.coverage

    print()
    print("=== APPLICATION FLOW ===")
    print(f"company_id: {result.company_id}")
    print(f"name: {result.company.name}")
    print(f"ticker: {result.company.ticker}")
    print(f"symbol: {result.company.symbol}")
    print(f"exchange: {result.company.exchange}")
    print(
        "fundamental_profile:",
        result.company.fundamental_profile,
    )

    print()
    print("[ONBOARDING]")

    for step in result.onboarding.steps:
        line = f"{step.name}: {step.status.value}"

        if step.processed is not None:
            line += f" processed={step.processed}"

        if step.detail is not None:
            line += f" detail={step.detail}"

        print(line)

    print(
        "summary:",
        f"success={result.onboarding.succeeded}",
        f"unavailable={result.onboarding.unavailable}",
        f"failed={result.onboarding.failed}",
    )

    print()
    print("[COVERAGE]")
    print(f"as_of_date: {coverage.as_of_date}")
    print(
        "availability:",
        coverage.availability.value,
    )
    print(
        "price_available:",
        coverage.price_available,
    )
    print(
        "fundamental_snapshot_available:",
        coverage.fundamental_snapshot_available,
    )
    print(
        "fundamental_growth_available:",
        coverage.fundamental_growth_available,
    )
    print(
        "forward_eps_period:",
        coverage.forward_eps_period or "n/a",
    )
    print(f"estimate_count: {coverage.estimate_count}")
    print(f"dividend_count: {coverage.dividend_count}")
    print(
        "missing_snapshot_metrics:",
        ",".join(
            metric.value
            for metric in coverage.missing_snapshot_metrics
        )
        or "none",
    )
    print(
        "missing_growth_metrics:",
        ",".join(
            metric.value
            for metric in coverage.missing_growth_metrics
        )
        or "none",
    )

    print()
    print("[ANALYSIS]")
    print(
        "availability:",
        describe_analysis_state(result),
    )

    if result.analysis is None:
        print("valuation: unavailable")
        print("fundamentals: unavailable")
    else:
        print(
            "valuation:",
            (
                "available"
                if result.analysis.valuation is not None
                else "unavailable"
            ),
        )
        print(
            "fundamentals:",
            (
                "available"
                if result.analysis.fundamentals is not None
                else "unavailable"
            ),
        )

    print()
    print("[RADAR]")
    print(f"eligible: {result.radar_eligible}")

    if result.radar_input is not None:
        print(
            "fiscal_period_end:",
            result.radar_input.fiscal_period_end,
        )

    if not coverage.fundamentals_available:
        print(
            "point_in_time_note: verified publication dates "
            "may be required before fundamental PIT analysis "
            "becomes available."
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _validate_selected_args(parser, args)

    if args.max_results <= 0:
        parser.error("--max-results must be greater than zero.")

    discovery_provider = YahooCompanyDiscoveryProvider()

    try:
        candidates = discover_companies(
            provider=discovery_provider,
            query=args.query,
            max_results=args.max_results,
        )
    except ValueError as exc:
        parser.error(str(exc))

    _print_candidates(candidates)

    if args.select is None:
        return 0

    if args.select > len(candidates):
        parser.error(
            "--select exceeds the number of discovery results."
        )

    candidate = candidates[args.select - 1]

    try:
        candidate = discovery_provider.enrich(candidate)

        as_of_date = args.as_of_date or args.end_date

        with connect(args.db_path) as connection:
            result = run_application_flow(
                connection=connection,
                candidate=candidate,
                exchange=args.exchange,
                fundamental_profile=args.fundamental_profile,
                price_provider=YahooPriceProvider(),
                fundamentals_provider=(
                    YahooFundamentalsProvider()
                ),
                estimate_provider=YahooEstimateProvider(),
                dividend_provider=YahooDividendProvider(),
                initial_price_date=args.initial_price_date,
                end_date=args.end_date,
                as_of_date=as_of_date,
                scenarios=DEFAULT_SCENARIOS,
                estimate_date=args.estimate_date,
                target_return=args.target_return,
                years=args.years,
            )
    except ValueError as exc:
        parser.error(str(exc))

    _print_result(result)

    return 1 if result.onboarding.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
