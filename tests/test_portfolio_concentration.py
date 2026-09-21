from datetime import date

import pytest

from src.portfolio import (
    PortfolioCurrencySummary,
    ValuedPortfolioPosition,
    ValuedPortfolioSnapshot,
)
from src.portfolio_concentration import (
    build_portfolio_concentration,
)


def position(
    company_id: int,
    currency: str,
    market_value: float,
) -> ValuedPortfolioPosition:
    return ValuedPortfolioPosition(
        company_id=company_id,
        currency=currency,
        quantity=1.0,
        average_cost=market_value,
        cost_basis=market_value,
        realized_profit_loss=0.0,
        price=market_value,
        price_date=date(2026, 2, 15),
        market_value=market_value,
        unrealized_profit_loss=0.0,
        unrealized_return=0.0,
        weight=None,
    )


def snapshot(
    positions: tuple[ValuedPortfolioPosition, ...],
    summaries: tuple[PortfolioCurrencySummary, ...],
) -> ValuedPortfolioSnapshot:
    return ValuedPortfolioSnapshot(
        as_of_date=date(2026, 2, 15),
        positions=positions,
        currency_summaries=summaries,
    )


def test_weights_include_cash_in_denominator():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 600.0),
            position(2, "EUR", 200.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=800.0,
                cash=200.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.invested_weight == pytest.approx(0.8)
    assert result.cash_weight == pytest.approx(0.2)

    assert result.positions[0].weight == pytest.approx(
        0.6
    )
    assert result.positions[1].weight == pytest.approx(
        0.2
    )


def test_position_and_cash_weights_sum_to_one():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 500.0),
            position(2, "EUR", 250.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=750.0,
                cash=250.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    total_weight = (
        sum(
            item.weight
            for item in result.positions
        )
        + result.cash_weight
    )

    assert total_weight == pytest.approx(1.0)


def test_largest_position_weight():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 500.0),
            position(2, "EUR", 300.0),
            position(3, "EUR", 100.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=900.0,
                cash=100.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.largest_position_weight == pytest.approx(
        0.5
    )


def test_top_three_weight():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 400.0),
            position(2, "EUR", 300.0),
            position(3, "EUR", 200.0),
            position(4, "EUR", 50.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=950.0,
                cash=50.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.top_3_weight == pytest.approx(0.9)


def test_hhi_includes_cash():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 500.0),
            position(2, "EUR", 300.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=800.0,
                cash=200.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    expected_hhi = (
        0.5**2
        + 0.3**2
        + 0.2**2
    )

    assert result.hhi == pytest.approx(
        expected_hhi
    )


def test_positions_are_sorted_by_weight():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 100.0),
            position(2, "EUR", 600.0),
            position(3, "EUR", 300.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=1000.0,
                cash=0.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert tuple(
        item.company_id
        for item in result.positions
    ) == (2, 3, 1)


def test_currencies_are_analyzed_separately():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 600.0),
            position(2, "USD", 300.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="USD",
                positions_market_value=300.0,
                cash=200.0,
                total_value=500.0,
            ),
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=600.0,
                cash=400.0,
                total_value=1000.0,
            ),
        ),
    )

    results = build_portfolio_concentration(
        portfolio
    )

    assert tuple(
        result.currency
        for result in results
    ) == ("EUR", "USD")

    eur, usd = results

    assert eur.positions[0].weight == pytest.approx(
        0.6
    )
    assert eur.cash_weight == pytest.approx(0.4)

    assert usd.positions[0].weight == pytest.approx(
        0.6
    )
    assert usd.cash_weight == pytest.approx(0.4)


def test_cash_only_currency():
    portfolio = snapshot(
        positions=(),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=0.0,
                cash=1000.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.position_count == 0
    assert result.positions == ()
    assert result.invested_weight == pytest.approx(0.0)
    assert result.cash_weight == pytest.approx(1.0)
    assert result.largest_position_weight is None
    assert result.top_3_weight is None
    assert result.hhi == pytest.approx(1.0)


def test_non_positive_total_has_no_weights():
    portfolio = snapshot(
        positions=(),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=0.0,
                cash=0.0,
                total_value=0.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.cash_weight is None
    assert result.invested_weight is None
    assert result.largest_position_weight is None
    assert result.top_3_weight is None
    assert result.hhi is None


def test_negative_cash_is_preserved():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 1200.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=1200.0,
                cash=-200.0,
                total_value=1000.0,
            ),
        ),
    )

    result = build_portfolio_concentration(
        portfolio
    )[0]

    assert result.invested_weight == pytest.approx(1.2)
    assert result.cash_weight == pytest.approx(-0.2)
    assert result.positions[0].weight == pytest.approx(
        1.2
    )

    assert (
        result.invested_weight
        + result.cash_weight
    ) == pytest.approx(1.0)


def test_invalid_total_identity_is_rejected():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 800.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=800.0,
                cash=100.0,
                total_value=1000.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="total_value must equal",
    ):
        build_portfolio_concentration(
            portfolio
        )


def test_position_values_must_match_summary():
    portfolio = snapshot(
        positions=(
            position(1, "EUR", 700.0),
        ),
        summaries=(
            PortfolioCurrencySummary(
                currency="EUR",
                positions_market_value=800.0,
                cash=200.0,
                total_value=1000.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="position market values do not match",
    ):
        build_portfolio_concentration(
            portfolio
        )


def test_empty_snapshot():
    portfolio = snapshot(
        positions=(),
        summaries=(),
    )

    assert build_portfolio_concentration(
        portfolio
    ) == ()