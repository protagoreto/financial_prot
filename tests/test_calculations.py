import pytest

from src.calculations import (
    dividend_yield,
    earnings_yield,
    free_cash_flow_yield,
    net_debt_to_ebitda,
    price_to_earnings,
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