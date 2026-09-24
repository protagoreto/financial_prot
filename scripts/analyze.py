import argparse
from datetime import date
from pathlib import Path
import sqlite3

from src.config import settings
from src.coverage import build_company_coverage
from src.db import connect
from src.investment import build_investment_analysis
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


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid ISO date: {value}"
        ) from exc


def _parse_scenario(values: list[str]) -> ValuationScenario:
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


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _number(
    value: float | None,
    decimals: int = 2,
) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Point-in-time investment analysis for one company."
        )
    )

    parser.add_argument(
        "ticker",
        help="Company ticker stored in the database.",
    )
    parser.add_argument(
        "--as-of-date",
        type=_parse_date,
        required=True,
        help="Point-in-time analysis date in YYYY-MM-DD.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=settings.db_path,
        help="SQLite database path.",
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
        "--scenario",
        nargs=4,
        action="append",
        metavar=(
            "NAME",
            "EPS_GROWTH",
            "DIVIDEND_YIELD",
            "TERMINAL_PE",
        ),
        help=(
            "Scenario assumptions. Repeat for multiple "
            "scenarios. Defaults are used when omitted."
        ),
    )

    return parser


def _get_company(
    connection: sqlite3.Connection,
    ticker: str,
) -> sqlite3.Row:
    rows = connection.execute(
        """
        SELECT
            company_id,
            name,
            ticker,
            exchange,
            currency,
            fundamental_profile
        FROM companies
        WHERE UPPER(ticker) = UPPER(?)
        AND status = 'active'
        ORDER BY company_id
        """,
        (ticker,),
    ).fetchall()

    if not rows:
        raise ValueError(
            f"Active company not found for ticker: {ticker}"
        )

    if len(rows) > 1:
        exchanges = ", ".join(
            str(row["exchange"])
            for row in rows
        )
        raise ValueError(
            f"Ticker {ticker} is ambiguous across exchanges: "
            f"{exchanges}"
        )

    return rows[0]


def _print_analysis(
    company: sqlite3.Row,
    analysis,
) -> None:
    print("=== INVESTMENT ANALYSIS ===")
    print(f"company: {company['name']}")
    print(f"ticker: {company['ticker']}")
    print(f"exchange: {company['exchange']}")
    print(
        "fundamental_profile:",
        company["fundamental_profile"],
    )
    print(f"as_of_date: {analysis.as_of_date}")
    print(f"availability: {analysis.availability.value}")

    print("\n[FORWARD VALUATION]")

    if analysis.valuation is None:
        print("unavailable")
    else:
        snapshot = analysis.valuation.snapshot

        print(f"price_date: {snapshot.price_date}")
        print(
            "price:",
            _number(snapshot.price),
            company["currency"],
        )
        print(
            "forward_eps:",
            _number(snapshot.forward_eps, 4),
        )
        print(
            "fiscal_period_end:",
            snapshot.fiscal_period_end,
        )
        print(
            "estimate_date:",
            snapshot.estimate_date,
        )
        print(
            "analyst_count:",
            snapshot.analyst_count,
        )
        print(
            "forward_pe:",
            _number(snapshot.forward_pe),
        )
        print(
            "forward_earnings_yield:",
            _percent(snapshot.forward_earnings_yield),
        )

    print("\n[FUNDAMENTALS]")

    if analysis.fundamentals is None:
        print("unavailable")
    else:
        assessment = analysis.fundamentals

        print(
            "quality_level:",
            assessment.quality_level.value,
        )
        print(
            "risk_level:",
            assessment.risk_level.value,
        )
        print(
            "value_trap_warning:",
            assessment.value_trap_warning,
        )
        print(
            "quality_signals:",
            (
                f"{assessment.positive_quality_signals}/"
                f"{assessment.known_quality_signals}"
            ),
        )
        print(
            "active_risk_signals:",
            (
                f"{assessment.active_risk_signals}/"
                f"{assessment.known_risk_signals}"
            ),
        )
        print(
            "quality_reasons:",
            ", ".join(assessment.quality_reasons) or "none",
        )
        print(
            "risk_reasons:",
            ", ".join(assessment.risk_reasons) or "none",
        )
        print(
            "value_trap_reasons:",
            (
                ", ".join(assessment.value_trap_reasons)
                or "none"
            ),
        )

    print("\n[SCENARIOS]")

    if analysis.valuation is None:
        print("unavailable")
    else:
        for result in analysis.valuation.scenarios:
            print(f"\n{result.name}:")
            print(
                "  eps_growth:",
                _percent(result.eps_growth),
            )
            print(
                "  dividend_yield:",
                _percent(result.dividend_yield),
            )
            print(
                "  terminal_pe:",
                _number(result.terminal_pe),
            )
            print(
                "  expected_return:",
                _percent(result.expected_return),
            )
            print(
                "  required_eps_growth:",
                _percent(result.required_eps_growth),
            )
            print(
                "  required_pe:",
                _number(result.required_pe),
            )
            print(
                "  required_price:",
                _number(result.required_price),
            )
            print(
                "  price_margin:",
                _percent(result.price_margin),
            )

    print("\n[VALUE CONDITIONS]")

    if analysis.value is None:
        print("unavailable")
    else:
        print(
            "target_return:",
            _percent(analysis.value.target_return),
        )

        for scenario in analysis.value.scenarios:
            print(
                f"{scenario.name}:",
                scenario.condition.value,
            )


def run_analysis(
    db_path: Path,
    ticker: str,
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float,
    years: int,
) -> int:
    if target_return <= -1.0:
        raise ValueError(
            "target_return must be greater than -1."
        )

    if years <= 0:
        raise ValueError(
            "years must be greater than zero."
        )

    if not scenarios:
        raise ValueError(
            "At least one scenario is required."
        )

    with connect(db_path) as connection:
        company = _get_company(
            connection=connection,
            ticker=ticker,
        )

        coverage = build_company_coverage(
            connection=connection,
            company_id=company["company_id"],
            as_of_date=as_of_date,
        )

        if coverage.forward_eps_period is None:
            raise ValueError(
                "No point-in-time forward EPS period is "
                f"available for {company['ticker']} on "
                f"{as_of_date}."
            )

        analysis = build_investment_analysis(
            connection=connection,
            company_id=company["company_id"],
            as_of_date=as_of_date,
            fiscal_period_end=coverage.forward_eps_period,
            scenarios=scenarios,
            target_return=target_return,
            years=years,
        )

        _print_analysis(
            company=company,
            analysis=analysis,
        )

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        scenarios = (
            tuple(
                _parse_scenario(values)
                for values in args.scenario
            )
            if args.scenario
            else DEFAULT_SCENARIOS
        )

        return run_analysis(
            db_path=args.db_path,
            ticker=args.ticker,
            as_of_date=args.as_of_date,
            scenarios=scenarios,
            target_return=args.target_return,
            years=args.years,
        )
    except (
        argparse.ArgumentTypeError,
        ValueError,
    ) as exc:
        parser.error(str(exc))

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
