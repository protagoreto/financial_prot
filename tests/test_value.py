from datetime import date

import pytest

from src.analysis import ValuationAnalysis
from src.scenarios import ScenarioResult
from src.value import (
    ValueCondition,
    assess_scenario_value,
    assess_value,
)
from src.valuation import ForwardValuationSnapshot


def make_result(
    name: str = "Base",
    expected_return: float | None = 0.12,
    required_price: float | None = 65.0,
    price_margin: float | None = 0.0833333333,
) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
        expected_return=expected_return,
        required_eps_growth=0.06,
        required_pe=21.6666666667,
        required_price=required_price,
        price_margin=price_margin,
    )


def make_valuation(
    scenarios: tuple[ScenarioResult, ...],
    target_return: float = 0.10,
) -> ValuationAnalysis:
    snapshot = ForwardValuationSnapshot(
        company_id=1,
        as_of_date=date(2026, 3, 1),
        price_date=date(2026, 3, 1),
        price=60.0,
        fiscal_period_end=date(2026, 12, 31),
        estimate_date=date(2026, 2, 25),
        analyst_count=12,
        forward_eps=3.0,
        forward_pe=20.0,
        forward_earnings_yield=0.05,
    )

    return ValuationAnalysis(
        company_id=1,
        as_of_date=date(2026, 3, 1),
        target_return=target_return,
        years=5,
        snapshot=snapshot,
        scenarios=scenarios,
    )


def test_scenario_target_met():
    result = make_result(
        expected_return=0.12,
        required_price=65.0,
        price_margin=0.08,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.10,
    )

    assert (
        assessment.condition
        == ValueCondition.TARGET_MET
    )
    assert assessment.expected_return == 0.12
    assert assessment.required_price == 65.0
    assert assessment.price_margin == 0.08


def test_scenario_target_not_met():
    result = make_result(
        expected_return=0.07,
        required_price=50.0,
        price_margin=-0.10,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.10,
    )

    assert (
        assessment.condition
        == ValueCondition.TARGET_NOT_MET
    )


@pytest.mark.parametrize(
    (
        "expected_return",
        "price_margin",
    ),
    [
        (None, 0.10),
        (0.12, None),
        (None, None),
    ],
)
def test_missing_result_is_unknown(
    expected_return,
    price_margin,
):
    result = make_result(
        expected_return=expected_return,
        price_margin=price_margin,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.10,
    )

    assert (
        assessment.condition
        == ValueCondition.UNKNOWN
    )


def test_inconsistent_results_are_unknown():
    result = make_result(
        expected_return=0.12,
        required_price=50.0,
        price_margin=-0.10,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.10,
    )

    assert (
        assessment.condition
        == ValueCondition.UNKNOWN
    )


def test_exact_target_is_met():
    result = make_result(
        expected_return=0.10,
        required_price=60.0,
        price_margin=0.0,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.10,
    )

    assert (
        assessment.condition
        == ValueCondition.TARGET_MET
    )


def test_value_assessment_preserves_scenarios():
    valuation = make_valuation(
        scenarios=(
            make_result(
                name="Conservative",
                expected_return=0.07,
                required_price=50.0,
                price_margin=-0.10,
            ),
            make_result(
                name="Base",
                expected_return=0.12,
                required_price=65.0,
                price_margin=0.08,
            ),
        )
    )

    assessment = assess_value(valuation)

    assert assessment.target_return == 0.10
    assert len(assessment.scenarios) == 2

    assert [
        scenario.name
        for scenario in assessment.scenarios
    ] == [
        "Conservative",
        "Base",
    ]

    assert (
        assessment.scenarios[0].condition
        == ValueCondition.TARGET_NOT_MET
    )

    assert (
        assessment.scenarios[1].condition
        == ValueCondition.TARGET_MET
    )


def test_target_return_is_not_hardcoded():
    result = make_result(
        expected_return=0.12,
        required_price=55.0,
        price_margin=-0.08,
    )

    assessment = assess_scenario_value(
        scenario=result,
        target_return=0.15,
    )

    assert (
        assessment.condition
        == ValueCondition.TARGET_NOT_MET
    )