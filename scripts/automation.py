import argparse
from datetime import date
from pathlib import Path
import sys

from src.automation import (
    RadarRunConfig,
    run_audited_radar,
    update_prices,
)
from src.config import settings
from src.db import connect, initialize_database
from src.message_runtime import get_message_runtime
from src.providers.yahoo import YahooPriceProvider
from src.radar_message_service import send_radar_report_row
from src.radar_report import build_radar_report
from src.scenarios import ValuationScenario
from src.universe import IBEX_UNIVERSE


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid ISO date: {value}"
        ) from exc


def _parse_scenario(
    values: list[str],
) -> ValuationScenario:
    name, eps_growth, dividend_yield, terminal_pe = values

    try:
        return ValuationScenario(
            name=name,
            eps_growth=float(eps_growth),
            dividend_yield=float(dividend_yield),
            terminal_pe=float(terminal_pe),
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid scenario: {' '.join(values)}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Value Investing System automation CLI."
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
        help="SQLite database path.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    prices_parser = subparsers.add_parser(
        "prices",
        help="Update market prices incrementally.",
    )

    prices_parser.add_argument(
        "--start-date",
        type=_parse_date,
        required=True,
        help="Initial ISO date YYYY-MM-DD.",
    )

    prices_parser.add_argument(
        "--end-date",
        type=_parse_date,
        required=True,
        help="Final ISO date YYYY-MM-DD.",
    )

    radar_parser = subparsers.add_parser(
        "radar",
        help="Run the audited Value Investing radar.",
    )

    radar_parser.add_argument(
        "--as-of-date",
        type=_parse_date,
        required=True,
        help="Point-in-time analysis date YYYY-MM-DD.",
    )

    radar_parser.add_argument(
        "--model-version",
        required=True,
        help="Explicit model version for the audit log.",
    )

    radar_parser.add_argument(
        "--data-version",
        required=True,
        help="Explicit data version for the audit log.",
    )

    radar_parser.add_argument(
        "--scenario",
        nargs=4,
        action="append",
        metavar=(
            "NAME",
            "EPS_GROWTH",
            "DIVIDEND_YIELD",
            "TERMINAL_PE",
        ),
        required=True,
        help=(
            "Scenario assumptions. Repeat --scenario "
            "for multiple scenarios."
        ),
    )

    radar_parser.add_argument(
        "--target-return",
        type=float,
        default=0.10,
    )

    radar_parser.add_argument(
        "--years",
        type=int,
        default=5,
    )

    radar_parser.add_argument(
        "--low-net-debt-threshold",
        type=float,
        default=2.0,
    )

    radar_parser.add_argument(
        "--notify",
        choices=("telegram",),
        default=None,
        help=(
            "Send radar report rows through the selected "
            "message provider."
        ),
    )

    radar_parser.add_argument(
        "--notify-scenario",
        default=None,
        help=(
            "Scenario name to send when --notify is used."
        ),
    )

    return parser


def _run_prices(
    db_path: Path,
    start_date: date,
    end_date: date,
) -> int:
    initialize_database(db_path)

    provider = YahooPriceProvider()

    with connect(db_path) as connection:
        result = update_prices(
            connection=connection,
            provider=provider,
            universe=IBEX_UNIVERSE,
            initial_start_date=start_date,
            end_date=end_date,
        )

    for company in result.companies:
        if company.error is None:
            print(
                f"{company.company.ticker}: "
                f"{company.processed_records} records"
            )
        else:
            print(
                f"{company.company.ticker}: "
                f"FAILED: {company.error}",
                file=sys.stderr,
            )

    print(
        f"Processed records: {result.processed_records}"
    )

    return 0 if result.is_complete else 1


def _run_radar(
    db_path: Path,
    as_of_date: date,
    model_version: str,
    data_version: str,
    scenario_values: list[list[str]],
    target_return: float,
    years: int,
    low_net_debt_threshold: float,
    notify: str | None,
    notify_scenario: str | None,
) -> int:
    if notify is not None and notify_scenario is None:
        raise ValueError(
            "--notify-scenario is required when "
            "--notify is used."
        )

    scenarios = tuple(
        _parse_scenario(values)
        for values in scenario_values
    )

    config = RadarRunConfig(
        universe=IBEX_UNIVERSE,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
        low_net_debt_threshold=low_net_debt_threshold,
    )

    initialize_database(db_path)

    with connect(db_path) as connection:
        result = run_audited_radar(
            connection=connection,
            config=config,
            as_of_date=as_of_date,
            model_version=model_version,
            data_version=data_version,
        )

    print(
        f"Radar entries: {len(result.snapshot.entries)}"
    )
    print(
        f"Unresolved companies: {len(result.unresolved)}"
    )

    if notify is not None:
        rows = build_radar_report(
            snapshot=result.snapshot,
            scenario_name=notify_scenario,
        )

        runtime = get_message_runtime(
            provider_name=notify,
        )

        for row in rows:
            send_radar_report_row(
                provider=runtime.provider,
                destination=runtime.destination,
                row=row,
            )

        print(
            f"Notifications sent: {len(rows)}"
        )

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prices":
        return _run_prices(
            db_path=args.db_path,
            start_date=args.start_date,
            end_date=args.end_date,
        )

    if args.command == "radar":
        if args.notify is not None and args.notify_scenario is None:
            parser.error(
                "--notify-scenario is required when --notify is used."
            )

        try:
            scenarios = [
                _parse_scenario(values)
                for values in args.scenario
            ]
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))

        return _run_radar(
            db_path=args.db_path,
            as_of_date=args.as_of_date,
            model_version=args.model_version,
            data_version=args.data_version,
            scenario_values=args.scenario,
            target_return=args.target_return,
            years=args.years,
            low_net_debt_threshold=(
                args.low_net_debt_threshold
            ),
            notify=args.notify,
            notify_scenario=args.notify_scenario,
        )

    parser.error(
        f"Unsupported command: {args.command}"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
