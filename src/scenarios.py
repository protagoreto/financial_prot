from dataclasses import dataclass

from src.calculations import (
    expected_annual_return,
    required_purchase_pe,
    required_purchase_price,
)


@dataclass(frozen=True)
class ValuationScenario:
    name: str
    eps_growth: float
    dividend_yield: float
    terminal_pe: float


@dataclass(frozen=True)
class ScenarioResult:
    name: str

    eps_growth: float
    dividend_yield: float
    terminal_pe: float

    expected_return: float | None
    required_pe: float | None
    required_price: float | None


def evaluate_scenario(
    scenario: ValuationScenario,
    current_pe: float,
    forward_eps: float,
    target_return: float,
    years: int = 5,
) -> ScenarioResult:
    expected_return = expected_annual_return(
        eps_growth=scenario.eps_growth,
        dividend_yield=scenario.dividend_yield,
        current_pe=current_pe,
        terminal_pe=scenario.terminal_pe,
        years=years,
    )

    required_pe = required_purchase_pe(
        target_return=target_return,
        eps_growth=scenario.eps_growth,
        dividend_yield=scenario.dividend_yield,
        terminal_pe=scenario.terminal_pe,
        years=years,
    )

    required_price = required_purchase_price(
        forward_eps=forward_eps,
        target_return=target_return,
        eps_growth=scenario.eps_growth,
        dividend_yield=scenario.dividend_yield,
        terminal_pe=scenario.terminal_pe,
        years=years,
    )

    return ScenarioResult(
        name=scenario.name,
        eps_growth=scenario.eps_growth,
        dividend_yield=scenario.dividend_yield,
        terminal_pe=scenario.terminal_pe,
        expected_return=expected_return,
        required_pe=required_pe,
        required_price=required_price,
    )


def evaluate_scenarios(
    scenarios: tuple[ValuationScenario, ...],
    current_pe: float,
    forward_eps: float,
    target_return: float,
    years: int = 5,
) -> tuple[ScenarioResult, ...]:
    return tuple(
        evaluate_scenario(
            scenario=scenario,
            current_pe=current_pe,
            forward_eps=forward_eps,
            target_return=target_return,
            years=years,
        )
        for scenario in scenarios
    )