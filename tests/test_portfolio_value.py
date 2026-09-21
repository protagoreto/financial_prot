from datetime import date

import pytest

from src.analysis import ValuationAnalysis
from src.portfolio_value import (
    PortfolioValuationStatus,
    build_portfolio_value_summaries,
    build_position_valuation,
)
from src.scenarios import ScenarioResult
from src.valuation import ForwardValuationSnapshot


def valuation(
    company_id: int,
    scenario_name: str = "base",
    expected_return: float | None = 0.12,
    required_price: float | None = 60.0,
    price_margin: float | None = 0.20,
) -> ValuationAnalysis:
    snapshot = ForwardValuationSnapshot(
    	company_id=company_id,
    	as_of_date=date(2026, 2, 15),
    	price=50.0,
    	price_date=date(2026, 2, 14),
    	forward_eps=5.0,
    	fiscal_period_end=date(2026, 12, 31),
    	estimate_date=date(2026, 2, 10),
    	analyst_count=10,
    	forward_pe=10.0,
    	forward_earnings_yield=0.10,
)

    scenario = ScenarioResult(
        name=scenario_name,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=12.0,
        expected_return=expected_return,
        required_eps_growth=0.05,
        required_pe=12.0,
        required_price=required_price,
        price_margin=price_margin,
    )

    return ValuationAnalysis(
        company_id=company_id,
        as_of_date=date(2026, 2, 15),
        target_return=0.10,
        years=5,
        snapshot=snapshot,
        scenarios=(scenario,),
    )


def test_available_position_valuation():
    result = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(company_id=1),
    )

    assert result.status == PortfolioValuationStatus.AVAILABLE
    assert result.expected_return == pytest.approx(0.12)
    assert result.required_price == pytest.approx(60)
    assert result.required_position_value == pytest.approx(600)
    assert result.value_gap == pytest.approx(100)


def test_missing_valuation_is_unavailable():
    result = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=None,
    )

    assert result.status == PortfolioValuationStatus.UNAVAILABLE
    assert result.expected_return is None
    assert result.required_price is None
    assert result.required_position_value is None
    assert result.value_gap is None


def test_missing_scenario_is_unavailable():
    result = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="bear",
        valuation=valuation(
            company_id=1,
            scenario_name="base",
        ),
    )

    assert result.status == PortfolioValuationStatus.UNAVAILABLE


def test_incomplete_scenario_is_unavailable():
    result = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            expected_return=None,
        ),
    )

    assert result.status == PortfolioValuationStatus.UNAVAILABLE


def test_wrong_company_valuation_is_rejected():
    with pytest.raises(
        ValueError,
        match="company_id",
    ):
        build_position_valuation(
            company_id=1,
            currency="EUR",
            quantity=10,
            market_value=500,
            weight=0.50,
            scenario_name="base",
            valuation=valuation(company_id=2),
        )


def test_currency_is_normalized():
    result = build_position_valuation(
        company_id=1,
        currency="eur",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=None,
    )

    assert result.currency == "EUR"


def test_summary_weighted_expected_return():
    first = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            expected_return=0.10,
            required_price=55,
            price_margin=0.10,
        ),
    )

    second = build_position_valuation(
        company_id=2,
        currency="EUR",
        quantity=5,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=2,
            expected_return=0.20,
            required_price=120,
            price_margin=0.20,
        ),
    )

    summary = build_portfolio_value_summaries(
        (first, second)
    )[0]

    assert summary.weighted_expected_return == pytest.approx(0.15)


def test_weighted_return_uses_market_value_not_position_count():
    first = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=900,
        weight=0.90,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            expected_return=0.10,
        ),
    )

    second = build_position_valuation(
        company_id=2,
        currency="EUR",
        quantity=1,
        market_value=100,
        weight=0.10,
        scenario_name="base",
        valuation=valuation(
            company_id=2,
            expected_return=0.30,
        ),
    )

    summary = build_portfolio_value_summaries(
        (first, second)
    )[0]

    assert summary.weighted_expected_return == pytest.approx(0.12)


def test_unavailable_position_is_excluded_from_weighted_return():
    available = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=600,
        weight=0.60,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            expected_return=0.15,
        ),
    )

    unavailable = build_position_valuation(
        company_id=2,
        currency="EUR",
        quantity=4,
        market_value=400,
        weight=0.40,
        scenario_name="base",
        valuation=None,
    )

    summary = build_portfolio_value_summaries(
        (available, unavailable)
    )[0]

    assert summary.total_market_value == pytest.approx(1000)
    assert summary.valued_market_value == pytest.approx(600)
    assert summary.unavailable_market_value == pytest.approx(400)
    assert summary.coverage == pytest.approx(0.60)

    # Never interpret the missing 40% as 0% return.
    assert summary.weighted_expected_return == pytest.approx(0.15)


def test_no_available_valuations_has_no_expected_return():
    position = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=1.0,
        scenario_name="base",
        valuation=None,
    )

    summary = build_portfolio_value_summaries(
        (position,)
    )[0]

    assert summary.coverage == pytest.approx(0)
    assert summary.weighted_expected_return is None
    assert summary.required_portfolio_value is None
    assert summary.value_gap is None


def test_required_portfolio_value_is_aggregated():
    first = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            required_price=60,
        ),
    )

    second = build_position_valuation(
        company_id=2,
        currency="EUR",
        quantity=5,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=2,
            required_price=120,
        ),
    )

    summary = build_portfolio_value_summaries(
        (first, second)
    )[0]

    assert summary.required_portfolio_value == pytest.approx(1200)
    assert summary.value_gap == pytest.approx(200)


def test_currencies_are_kept_separate():
    eur = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=1.0,
        scenario_name="base",
        valuation=valuation(company_id=1),
    )

    usd = build_position_valuation(
        company_id=2,
        currency="USD",
        quantity=10,
        market_value=1000,
        weight=1.0,
        scenario_name="base",
        valuation=valuation(company_id=2),
    )

    summaries = build_portfolio_value_summaries(
        (eur, usd)
    )

    assert len(summaries) == 2
    assert summaries[0].currency == "EUR"
    assert summaries[0].total_market_value == pytest.approx(500)
    assert summaries[1].currency == "USD"
    assert summaries[1].total_market_value == pytest.approx(1000)


def test_mixed_scenarios_in_same_summary_are_rejected():
    base = build_position_valuation(
        company_id=1,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="base",
        valuation=valuation(
            company_id=1,
            scenario_name="base",
        ),
    )

    bear = build_position_valuation(
        company_id=2,
        currency="EUR",
        quantity=10,
        market_value=500,
        weight=0.50,
        scenario_name="bear",
        valuation=valuation(
            company_id=2,
            scenario_name="bear",
        ),
    )

    with pytest.raises(
        ValueError,
        match="same scenario",
    ):
        build_portfolio_value_summaries(
            (base, bear)
        )


def test_empty_portfolio_has_no_summaries():
    assert build_portfolio_value_summaries(()) == ()