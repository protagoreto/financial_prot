from dataclasses import dataclass
from enum import Enum

from src.analysis import ValuationAnalysis
from src.scenarios import ScenarioResult


class ValueCondition(str, Enum):
    TARGET_MET = "target_met"
    TARGET_NOT_MET = "target_not_met"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScenarioValueAssessment:
    name: str

    target_return: float

    expected_return: float | None
    required_price: float | None
    price_margin: float | None

    condition: ValueCondition


@dataclass(frozen=True)
class ValueAssessment:
    target_return: float
    scenarios: tuple[ScenarioValueAssessment, ...]


def assess_value(
    valuation: ValuationAnalysis,
) -> ValueAssessment:
    scenario_assessments = tuple(
        assess_scenario_value(
            scenario=result,
            target_return=valuation.target_return,
        )
        for result in valuation.scenarios
    )

    return ValueAssessment(
        target_return=valuation.target_return,
        scenarios=scenario_assessments,
    )


def assess_scenario_value(
    scenario: ScenarioResult,
    target_return: float,
) -> ScenarioValueAssessment:
    condition = _value_condition(
        expected_return=scenario.expected_return,
        price_margin=scenario.price_margin,
        target_return=target_return,
    )

    return ScenarioValueAssessment(
        name=scenario.name,
        target_return=target_return,
        expected_return=scenario.expected_return,
        required_price=scenario.required_price,
        price_margin=scenario.price_margin,
        condition=condition,
    )


def _value_condition(
    expected_return: float | None,
    price_margin: float | None,
    target_return: float,
    tolerance: float = 1e-12,
) -> ValueCondition:
    if (
        expected_return is None
        or price_margin is None
    ):
        return ValueCondition.UNKNOWN

    return_meets_target = (
        expected_return
        >= target_return - tolerance
    )

    price_meets_target = (
        price_margin >= -tolerance
    )

    if return_meets_target != price_meets_target:
        return ValueCondition.UNKNOWN

    if return_meets_target:
        return ValueCondition.TARGET_MET

    return ValueCondition.TARGET_NOT_MET