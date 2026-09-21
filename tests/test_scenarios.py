import pytest

from src.calculations import required_eps_growth
from src.scenarios import (
    ValuationScenario,
    evaluate_scenario,
    evaluate_scenarios,
)


def test_evaluate_scenario():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    result = evaluate_scenario(
        scenario=scenario,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    assert result.name == "Base"

    assert result.eps_growth == 0.08
    assert result.dividend_yield == 0.02
    assert result.terminal_pe == 15.0

    assert result.expected_return is not None
    assert result.required_eps_growth is not None
    assert result.required_pe is not None
    assert result.required_price is not None

    assert result.required_price == pytest.approx(
        result.required_pe * 3.0
    )


def test_required_eps_growth_matches_calculation():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    result = evaluate_scenario(
        scenario=scenario,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    expected_required_growth = required_eps_growth(
        target_return=0.10,
        dividend_yield=0.02,
        current_pe=20.0,
        terminal_pe=15.0,
        years=5,
    )

    assert result.required_eps_growth == pytest.approx(
        expected_required_growth
    )


def test_required_eps_growth_does_not_depend_on_assumed_growth():
    low_growth = ValuationScenario(
        name="Low growth",
        eps_growth=0.03,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    high_growth = ValuationScenario(
        name="High growth",
        eps_growth=0.12,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    low_result = evaluate_scenario(
        scenario=low_growth,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    high_result = evaluate_scenario(
        scenario=high_growth,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    assert (
        low_result.required_eps_growth
        == pytest.approx(
            high_result.required_eps_growth
        )
    )


def test_higher_current_pe_requires_more_growth():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    lower_pe_result = evaluate_scenario(
        scenario=scenario,
        current_pe=15.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    higher_pe_result = evaluate_scenario(
        scenario=scenario,
        current_pe=25.0,
        forward_eps=3.0,
        target_return=0.10,
        years=5,
    )

    assert (
        higher_pe_result.required_eps_growth
        > lower_pe_result.required_eps_growth
    )


def test_scenarios_preserve_input_order():
    scenarios = (
        ValuationScenario(
            name="Conservative",
            eps_growth=0.03,
            dividend_yield=0.02,
            terminal_pe=12.0,
        ),
        ValuationScenario(
            name="Base",
            eps_growth=0.08,
            dividend_yield=0.02,
            terminal_pe=15.0,
        ),
        ValuationScenario(
            name="Optimistic",
            eps_growth=0.12,
            dividend_yield=0.02,
            terminal_pe=18.0,
        ),
    )

    results = evaluate_scenarios(
        scenarios=scenarios,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
    )

    assert [
        result.name
        for result in results
    ] == [
        "Conservative",
        "Base",
        "Optimistic",
    ]


def test_more_favorable_scenario_increases_expected_return():
    conservative = ValuationScenario(
        name="Conservative",
        eps_growth=0.03,
        dividend_yield=0.02,
        terminal_pe=12.0,
    )

    optimistic = ValuationScenario(
        name="Optimistic",
        eps_growth=0.12,
        dividend_yield=0.02,
        terminal_pe=18.0,
    )

    conservative_result = evaluate_scenario(
        scenario=conservative,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
    )

    optimistic_result = evaluate_scenario(
        scenario=optimistic,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
    )

    assert (
        optimistic_result.expected_return
        > conservative_result.expected_return
    )


def test_more_favorable_scenario_allows_higher_purchase_price():
    conservative = ValuationScenario(
        name="Conservative",
        eps_growth=0.03,
        dividend_yield=0.02,
        terminal_pe=12.0,
    )

    optimistic = ValuationScenario(
        name="Optimistic",
        eps_growth=0.12,
        dividend_yield=0.02,
        terminal_pe=18.0,
    )

    conservative_result = evaluate_scenario(
        scenario=conservative,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
    )

    optimistic_result = evaluate_scenario(
        scenario=optimistic,
        current_pe=20.0,
        forward_eps=3.0,
        target_return=0.10,
    )

    assert (
        optimistic_result.required_price
        > conservative_result.required_price
    )