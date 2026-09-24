from datetime import date

import pytest

from scripts.analyze import (
    DEFAULT_SCENARIOS,
    _number,
    _parse_date,
    _parse_scenario,
    _percent,
    build_parser,
)


def test_parse_date_accepts_iso_date() -> None:
    assert _parse_date("2026-09-24") == date(
        2026,
        9,
        24,
    )


def test_parse_date_rejects_invalid_date() -> None:
    with pytest.raises(Exception):
        _parse_date("24-09-2026")


def test_parse_scenario_builds_typed_scenario() -> None:
    scenario = _parse_scenario(
        ["base", "0.06", "0.03", "14"]
    )

    assert scenario.name == "base"
    assert scenario.eps_growth == pytest.approx(0.06)
    assert scenario.dividend_yield == pytest.approx(0.03)
    assert scenario.terminal_pe == pytest.approx(14.0)


def test_parser_requires_ticker_and_as_of_date() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "BBVA",
            "--as-of-date",
            "2026-09-24",
        ]
    )

    assert args.ticker == "BBVA"
    assert args.as_of_date == date(2026, 9, 24)
    assert args.target_return == pytest.approx(0.10)
    assert args.years == 5


def test_default_scenarios_are_explicit() -> None:
    assert tuple(
        scenario.name
        for scenario in DEFAULT_SCENARIOS
    ) == (
        "conservative",
        "base",
        "optimistic",
    )


def test_formatters_handle_values_and_none() -> None:
    assert _percent(0.1234) == "12.34%"
    assert _percent(None) == "n/a"
    assert _number(12.3456) == "12.35"
    assert _number(12.3456, 4) == "12.3456"
    assert _number(None) == "n/a"
