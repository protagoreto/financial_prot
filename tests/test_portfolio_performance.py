from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.models import PortfolioTransaction, PriceRecord
from src.portfolio import build_portfolio_performance_snapshot
from src.repository import (
    insert_portfolio_transaction,
    insert_price_record,
)


def create_company(
    connection,
    name: str = "Test Company",
    ticker: str = "TEST",
    currency: str = "EUR",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO companies (
            name,
            ticker,
            exchange,
            currency
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            ticker,
            "BME",
            currency,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def add_transaction(
    connection,
    external_id: str,
    transaction_date: str,
    transaction_type: str,
    currency: str = "EUR",
    company_id: int | None = None,
    quantity: float | None = None,
    price: float | None = None,
    amount: float | None = None,
    fee: float = 0.0,
    tax: float = 0.0,
) -> None:
    insert_portfolio_transaction(
        connection,
        PortfolioTransaction(
            external_id=external_id,
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            currency=currency,
            company_id=company_id,
            quantity=quantity,
            price=price,
            amount=amount,
            fee=fee,
            tax=tax,
        ),
    )


def add_price(
    connection,
    company_id: int,
    price_date: str,
    close: float,
    currency: str = "EUR",
) -> None:
    insert_price_record(
        connection,
        PriceRecord(
            company_id=company_id,
            price_date=price_date,
            close=close,
            currency=currency,
        ),
    )


def test_dividend_income_is_reported_separately(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "dividend-1",
            "2026-02-01",
            "dividend",
            company_id=company_id,
            amount=25,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.gross_dividends == pytest.approx(25)
    assert summary.net_dividends == pytest.approx(25)
    assert summary.realized_profit_loss == pytest.approx(0)
    assert summary.unrealized_profit_loss == pytest.approx(0)
    assert summary.economic_profit_loss == pytest.approx(25)


def test_dividend_tax_and_fee_reduce_net_dividend(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "dividend-1",
            "2026-02-01",
            "dividend",
            company_id=company_id,
            amount=100,
            fee=2,
            tax=19,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.gross_dividends == pytest.approx(100)
    assert summary.dividend_fees == pytest.approx(2)
    assert summary.dividend_taxes == pytest.approx(19)
    assert summary.net_dividends == pytest.approx(79)
    assert summary.economic_profit_loss == pytest.approx(79)


def test_unrealized_profit_is_in_economic_profit(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_price(
            connection,
            company_id,
            "2026-02-01",
            60,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.realized_profit_loss == pytest.approx(0)
    assert summary.unrealized_profit_loss == pytest.approx(100)
    assert summary.net_dividends == pytest.approx(0)
    assert summary.economic_profit_loss == pytest.approx(100)


def test_realized_profit_survives_closed_position(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_transaction(
            connection,
            "sell-1",
            "2026-02-01",
            "sell",
            company_id=company_id,
            quantity=10,
            price=60,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.realized_profit_loss == pytest.approx(100)
    assert summary.unrealized_profit_loss == pytest.approx(0)
    assert summary.economic_profit_loss == pytest.approx(100)


def test_realized_unrealized_and_dividends_are_combined(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_transaction(
            connection,
            "sell-1",
            "2026-02-01",
            "sell",
            company_id=company_id,
            quantity=4,
            price=70,
        )

        add_transaction(
            connection,
            "dividend-1",
            "2026-02-05",
            "dividend",
            company_id=company_id,
            amount=20,
            tax=5,
        )

        add_price(
            connection,
            company_id,
            "2026-02-10",
            60,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    # Realized:
    # 4 * (70 - 50) = 80
    assert summary.realized_profit_loss == pytest.approx(80)

    # Remaining:
    # 6 shares * 60 = 360
    # remaining cost basis = 300
    assert summary.unrealized_profit_loss == pytest.approx(60)

    assert summary.net_dividends == pytest.approx(15)

    assert summary.economic_profit_loss == pytest.approx(155)


def test_buy_fee_is_not_double_counted(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
            fee=10,
        )

        add_price(
            connection,
            company_id,
            "2026-02-01",
            60,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    # Cost basis = 510.
    # Market value = 600.
    # Fee is already embedded in cost basis.
    assert summary.unrealized_profit_loss == pytest.approx(90)
    assert summary.economic_profit_loss == pytest.approx(90)


def test_sell_fee_is_not_double_counted(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_transaction(
            connection,
            "sell-1",
            "2026-02-01",
            "sell",
            company_id=company_id,
            quantity=10,
            price=60,
            fee=10,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    # Net proceeds = 590.
    # Cost basis = 500.
    assert summary.realized_profit_loss == pytest.approx(90)
    assert summary.economic_profit_loss == pytest.approx(90)


def test_cash_deposit_is_not_profit(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=10000,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    assert snapshot.income_summaries == ()


def test_future_dividend_is_excluded(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "dividend-1",
            "2026-02-01",
            "dividend",
            company_id=company_id,
            amount=20,
        )

        add_transaction(
            connection,
            "dividend-future",
            "2026-03-01",
            "dividend",
            company_id=company_id,
            amount=100,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.gross_dividends == pytest.approx(20)
    assert summary.net_dividends == pytest.approx(20)


def test_currencies_are_kept_separate(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_eur = create_company(
            connection,
            name="EUR Company",
            ticker="EURC",
            currency="EUR",
        )

        company_usd = create_company(
            connection,
            name="USD Company",
            ticker="USDC",
            currency="USD",
        )

        add_transaction(
            connection,
            "eur-dividend",
            "2026-02-01",
            "dividend",
            currency="EUR",
            company_id=company_eur,
            amount=20,
        )

        add_transaction(
            connection,
            "usd-dividend",
            "2026-02-01",
            "dividend",
            currency="USD",
            company_id=company_usd,
            amount=30,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summaries = {
        summary.currency: summary
        for summary in snapshot.income_summaries
    }

    assert len(summaries) == 2

    assert summaries["EUR"].net_dividends == pytest.approx(20)
    assert summaries["USD"].net_dividends == pytest.approx(30)

    assert summaries["EUR"].economic_profit_loss == pytest.approx(20)
    assert summaries["USD"].economic_profit_loss == pytest.approx(30)


def test_closed_position_profit_and_dividend_remain_visible(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_transaction(
            connection,
            "dividend-1",
            "2026-01-20",
            "dividend",
            company_id=company_id,
            amount=20,
            tax=5,
        )

        add_transaction(
            connection,
            "sell-1",
            "2026-02-01",
            "sell",
            company_id=company_id,
            quantity=10,
            price=60,
        )

        snapshot = build_portfolio_performance_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.income_summaries[0]

    assert summary.realized_profit_loss == pytest.approx(100)
    assert summary.unrealized_profit_loss == pytest.approx(0)
    assert summary.net_dividends == pytest.approx(15)
    assert summary.economic_profit_loss == pytest.approx(115)