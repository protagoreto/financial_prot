import pytest


from src.calculations import (
    calculate_free_cash_flow,
    calculate_net_debt,
    dividend_yield,
    earnings_yield,
    expected_annual_return,
    free_cash_flow_yield,
    growth_rate,
    net_debt_to_ebitda,
    price_to_earnings,
    required_eps_growth,
    required_purchase_pe,
    required_purchase_price,
    growth_rate,
    margin,
    net_debt_to_ebitda,
)

def test_price_to_earnings():
    assert price_to_earnings(
        price=50.0,
        eps=2.5,
    ) == pytest.approx(20.0)


def test_price_to_earnings_rejects_negative_eps():
    assert price_to_earnings(
        price=50.0,
        eps=-2.5,
    ) is None


def test_earnings_yield():
    assert earnings_yield(
        price=50.0,
        eps=2.5,
    ) == pytest.approx(0.05)


def test_dividend_yield():
    assert dividend_yield(
        price=50.0,
        dividend_per_share=1.5,
    ) == pytest.approx(0.03)


def test_free_cash_flow_yield():
    assert free_cash_flow_yield(
        market_cap=1_000.0,
        free_cash_flow=80.0,
    ) == pytest.approx(0.08)


def test_negative_free_cash_flow_is_preserved():
    assert free_cash_flow_yield(
        market_cap=1_000.0,
        free_cash_flow=-80.0,
    ) == pytest.approx(-0.08)


def test_net_debt_to_ebitda():
    assert net_debt_to_ebitda(
        net_debt=200.0,
        ebitda=100.0,
    ) == pytest.approx(2.0)


def test_net_cash_produces_negative_ratio():
    assert net_debt_to_ebitda(
        net_debt=-100.0,
        ebitda=200.0,
    ) == pytest.approx(-0.5)


def test_net_debt_to_ebitda_rejects_negative_ebitda():
    assert net_debt_to_ebitda(
        net_debt=100.0,
        ebitda=-20.0,
    ) is None

def test_expected_return_with_stable_multiple():
    result = expected_annual_return(
        eps_growth=0.08,
        dividend_yield=0.02,
        current_pe=15.0,
        terminal_pe=15.0,
        years=5,
    )

    assert result == pytest.approx(
        (1.08 * 1.02) - 1
    )


def test_expected_return_includes_multiple_compression():
    result = expected_annual_return(
        eps_growth=0.10,
        dividend_yield=0.02,
        current_pe=20.0,
        terminal_pe=15.0,
        years=5,
    )

    expected = (
        1.10
        * 1.02
        * (15.0 / 20.0) ** (1 / 5)
        - 1
    )

    assert result == pytest.approx(expected)


def test_required_eps_growth_reaches_target_return():
    growth = required_eps_growth(
        target_return=0.10,
        dividend_yield=0.02,
        current_pe=20.0,
        terminal_pe=15.0,
        years=5,
    )

    result = expected_annual_return(
        eps_growth=growth,
        dividend_yield=0.02,
        current_pe=20.0,
        terminal_pe=15.0,
        years=5,
    )

    assert result == pytest.approx(0.10)


def test_required_purchase_pe_reaches_target_return():
    purchase_pe = required_purchase_pe(
        target_return=0.10,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
        years=5,
    )

    result = expected_annual_return(
        eps_growth=0.08,
        dividend_yield=0.02,
        current_pe=purchase_pe,
        terminal_pe=15.0,
        years=5,
    )

    assert result == pytest.approx(0.10)


def test_required_purchase_price():
    purchase_pe = required_purchase_pe(
        target_return=0.10,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
        years=5,
    )

    price = required_purchase_price(
        forward_eps=3.0,
        target_return=0.10,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
        years=5,
    )

    assert price == pytest.approx(
        3.0 * purchase_pe
    )


def test_required_purchase_price_rejects_negative_eps():
    assert required_purchase_price(
        forward_eps=-1.0,
        target_return=0.10,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
        years=5,
    ) is None

def test_calculate_free_cash_flow():
    result = calculate_free_cash_flow(
        operating_cash_flow=9_232_000_000.0,
        capex=2_712_000_000.0,
    )

    assert result == pytest.approx(
        6_520_000_000.0
    )


def test_free_cash_flow_rejects_negative_capex():
    result = calculate_free_cash_flow(
        operating_cash_flow=9_232_000_000.0,
        capex=-2_712_000_000.0,
    )

    assert result is None

def test_calculate_net_debt():
    result = calculate_net_debt(
        total_debt=6_095_000_000.0,
        cash=8_000_000_000.0,
    )

    assert result == pytest.approx(
        -1_905_000_000.0
    )


def test_net_debt_allows_net_cash_position():
    result = calculate_net_debt(
        total_debt=2_000_000_000.0,
        cash=5_000_000_000.0,
    )

    assert result == pytest.approx(
        -3_000_000_000.0
    )


def test_net_debt_rejects_negative_debt():
    assert calculate_net_debt(
        total_debt=-1.0,
        cash=100.0,
    ) is None


def test_net_debt_rejects_negative_cash():
    assert calculate_net_debt(
        total_debt=100.0,
        cash=-1.0,
    ) is None

def test_growth_rate_positive():
    result = growth_rate(
        current_value=110.0,
        previous_value=100.0,
    )

    assert result == pytest.approx(0.10)


def test_growth_rate_negative():
    result = growth_rate(
        current_value=90.0,
        previous_value=100.0,
    )

    assert result == pytest.approx(-0.10)


def test_growth_rate_no_change():
    result = growth_rate(
        current_value=100.0,
        previous_value=100.0,
    )

    assert result == pytest.approx(0.0)


def test_growth_rate_rejects_zero_previous_value():
    result = growth_rate(
        current_value=100.0,
        previous_value=0.0,
    )

    assert result is None


def test_growth_rate_preserves_negative_values():
    result = growth_rate(
        current_value=-50.0,
        previous_value=-100.0,
    )

    assert result == pytest.approx(-0.50)

def test_margin_positive():
    result = margin(
        value=20.0,
        revenue=100.0,
    )

    assert result == pytest.approx(0.20)


def test_margin_negative():
    result = margin(
        value=-10.0,
        revenue=100.0,
    )

    assert result == pytest.approx(-0.10)


def test_margin_zero():
    result = margin(
        value=0.0,
        revenue=100.0,
    )

    assert result == pytest.approx(0.0)


def test_margin_rejects_zero_revenue():
    assert margin(
        value=20.0,
        revenue=0.0,
    ) is None


def test_margin_rejects_negative_revenue():
    assert margin(
        value=20.0,
        revenue=-100.0,
    ) is None