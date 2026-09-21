from dataclasses import dataclass
from enum import Enum

from src.analysis import ValuationAnalysis


class PortfolioValuationStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class PortfolioPositionValuation:
    company_id: int
    currency: str
    quantity: float
    market_value: float
    weight: float | None

    scenario_name: str
    status: PortfolioValuationStatus

    expected_return: float | None
    required_price: float | None
    price_margin: float | None

    required_position_value: float | None
    value_gap: float | None


@dataclass(frozen=True)
class PortfolioValueSummary:
    currency: str
    scenario_name: str

    total_market_value: float
    valued_market_value: float
    unavailable_market_value: float

    coverage: float | None

    weighted_expected_return: float | None
    required_portfolio_value: float | None
    value_gap: float | None


def build_position_valuation(
    company_id: int,
    currency: str,
    quantity: float,
    market_value: float,
    weight: float | None,
    scenario_name: str,
    valuation: ValuationAnalysis | None,
) -> PortfolioPositionValuation:
    if valuation is None:
        return _unavailable_position_valuation(
            company_id=company_id,
            currency=currency,
            quantity=quantity,
            market_value=market_value,
            weight=weight,
            scenario_name=scenario_name,
        )

    if valuation.company_id != company_id:
        raise ValueError(
            "valuation company_id does not match position company_id"
        )

    scenario = next(
        (
            result
            for result in valuation.scenarios
            if result.name == scenario_name
        ),
        None,
    )

    if scenario is None:
        return _unavailable_position_valuation(
            company_id=company_id,
            currency=currency,
            quantity=quantity,
            market_value=market_value,
            weight=weight,
            scenario_name=scenario_name,
        )

    if (
        scenario.expected_return is None
        or scenario.required_price is None
        or scenario.price_margin is None
    ):
        return _unavailable_position_valuation(
            company_id=company_id,
            currency=currency,
            quantity=quantity,
            market_value=market_value,
            weight=weight,
            scenario_name=scenario_name,
        )

    required_position_value = (
        quantity * scenario.required_price
    )

    value_gap = (
        required_position_value
        - market_value
    )

    return PortfolioPositionValuation(
        company_id=company_id,
        currency=currency.upper(),
        quantity=quantity,
        market_value=market_value,
        weight=weight,
        scenario_name=scenario_name,
        status=PortfolioValuationStatus.AVAILABLE,
        expected_return=scenario.expected_return,
        required_price=scenario.required_price,
        price_margin=scenario.price_margin,
        required_position_value=required_position_value,
        value_gap=value_gap,
    )


def build_portfolio_value_summaries(
    positions: tuple[PortfolioPositionValuation, ...],
) -> tuple[PortfolioValueSummary, ...]:
    currencies = sorted(
        {
            position.currency
            for position in positions
        }
    )

    summaries: list[PortfolioValueSummary] = []

    for currency in currencies:
        currency_positions = tuple(
            position
            for position in positions
            if position.currency == currency
        )

        scenario_names = {
            position.scenario_name
            for position in currency_positions
        }

        if len(scenario_names) != 1:
            raise ValueError(
                "all positions in a currency summary "
                "must use the same scenario"
            )

        scenario_name = next(iter(scenario_names))

        total_market_value = sum(
            position.market_value
            for position in currency_positions
        )

        available_positions = tuple(
            position
            for position in currency_positions
            if (
                position.status
                == PortfolioValuationStatus.AVAILABLE
            )
        )

        valued_market_value = sum(
            position.market_value
            for position in available_positions
        )

        unavailable_market_value = (
            total_market_value
            - valued_market_value
        )

        if total_market_value > 0:
            coverage = (
                valued_market_value
                / total_market_value
            )
        else:
            coverage = None

        if valued_market_value > 0:
            weighted_expected_return = (
                sum(
                    position.market_value
                    * position.expected_return
                    for position in available_positions
                    if position.expected_return is not None
                )
                / valued_market_value
            )
        else:
            weighted_expected_return = None

        if available_positions:
            required_portfolio_value = sum(
                position.required_position_value
                for position in available_positions
                if position.required_position_value is not None
            )

            value_gap = (
                required_portfolio_value
                - valued_market_value
            )
        else:
            required_portfolio_value = None
            value_gap = None

        summaries.append(
            PortfolioValueSummary(
                currency=currency,
                scenario_name=scenario_name,
                total_market_value=total_market_value,
                valued_market_value=valued_market_value,
                unavailable_market_value=unavailable_market_value,
                coverage=coverage,
                weighted_expected_return=weighted_expected_return,
                required_portfolio_value=required_portfolio_value,
                value_gap=value_gap,
            )
        )

    return tuple(summaries)


def _unavailable_position_valuation(
    company_id: int,
    currency: str,
    quantity: float,
    market_value: float,
    weight: float | None,
    scenario_name: str,
) -> PortfolioPositionValuation:
    return PortfolioPositionValuation(
        company_id=company_id,
        currency=currency.upper(),
        quantity=quantity,
        market_value=market_value,
        weight=weight,
        scenario_name=scenario_name,
        status=PortfolioValuationStatus.UNAVAILABLE,
        expected_return=None,
        required_price=None,
        price_margin=None,
        required_position_value=None,
        value_gap=None,
    )