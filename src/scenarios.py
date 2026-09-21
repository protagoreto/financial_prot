from dataclasses import dataclass

from src.calculations import (
    expected_annual_return,
    required_eps_growth,
    required_purchase_pe,
    required_purchase_price,
)


@dataclass(frozen=True)
class ValuationScenario:
    name: str

    # Explicit assumptions.
    eps_growth: float
    dividend_yield: float
    terminal_pe: float


@dataclass(frozen=True)
class ScenarioResult:
    name: str

    # Assumptions.
    eps_growth: float
    dividend_yield: float
    terminal_pe: float

    # Calculated outputs.
    expected_return: float | None
    required_eps_growth: float | None
    required_pe: float | None
    required_price: float | None
    price_margin: float | None


def calculate_price_margin(
    current_price: float,
    required_price: float | None,
) -> float | None:
    if current_price <= 0:
        return None

    if required_price is None or required_price <= 0:
        return None

    return required_price / current_price - 1


def evaluate_scenario(
    scenario: ValuationScenario,
    current_pe: float,
    current_price: float,
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

    required_growth = required_eps_growth(
        target_return=target_return,
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

    price_margin = calculate_price_margin(
        current_price=current_price,
        required_price=required_price,
    )

    return ScenarioResult(
        name=scenario.name,
        eps_growth=scenario.eps_growth,
        dividend_yield=scenario.dividend_yield,
        terminal_pe=scenario.terminal_pe,
        expected_return=expected_return,
        required_eps_growth=required_growth,
        required_pe=required_pe,
        required_price=required_price,
        price_margin=price_margin,
    )


def evaluate_scenarios(
    scenarios: tuple[ValuationScenario, ...],
    current_pe: float,
    current_price: float,
    forward_eps: float,
    target_return: float,
    years: int = 5,
) -> tuple[ScenarioResult, ...]:
    return tuple(
        evaluate_scenario(
            scenario=scenario,
            current_pe=current_pe,
            current_price=current_price,
            forward_eps=forward_eps,
            target_return=target_return,
            years=years,
        )
        for scenario in scenarios
    )