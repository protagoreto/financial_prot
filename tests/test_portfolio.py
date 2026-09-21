from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.models import PortfolioTransaction
from src.portfolio import (
    PortfolioCalculationError,
    build_portfolio_snapshot,
    build_portfolio_snapshot_from_transactions,
)
from src.repository import insert_portfolio_transaction


def transaction(
    external_id: str,
    transaction_date: str,
    transaction_type: str,
    company_id: int | None = 1,
    quantity: float | None = None,
    price: float | None = None,
    amount: float | None = None,
    fee: float = 0.0,
    tax: float = 0.0,
    currency: str = "EUR",
) -> PortfolioTransaction:
    return PortfolioTransaction(
        external_id=external_id,
        transaction_date=transaction_date,
        transaction_type=transaction_type,
        company_id=company_id,
        quantity=quantity,
        price=price,
        amount=amount,
        fee=fee,
        tax=tax,
        currency=currency,
    )


def create_company(connection) -> int:
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
            "Test Company",
            "TEST",
            "BME",
            "EUR",
        ),
    )

    connection.commit()

    return cursor.lastrowid


def test_single_buy_builds_position():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(10)
    assert position.cost_basis == pytest.approx(500)
    assert position.average_cost == pytest.approx(50)
    assert position.realized_profit_loss == pytest.approx(0)


def test_buy_fees_and_taxes_enter_cost_basis():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
                fee=5,
                tax=2,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.cost_basis == pytest.approx(507)
    assert position.average_cost == pytest.approx(50.7)
    assert position.total_buy_fees == pytest.approx(5)
    assert position.total_buy_taxes == pytest.approx(2)


def test_multiple_buys_use_weighted_average_cost():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="buy-2",
                transaction_date="2026-02-10",
                transaction_type="buy",
                quantity=10,
                price=70,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(20)
    assert position.cost_basis == pytest.approx(1200)
    assert position.average_cost == pytest.approx(60)


def test_partial_sell_realizes_profit():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="sell-1",
                transaction_date="2026-02-10",
                transaction_type="sell",
                quantity=4,
                price=70,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(6)
    assert position.average_cost == pytest.approx(50)
    assert position.cost_basis == pytest.approx(300)
    assert position.realized_profit_loss == pytest.approx(80)


def test_sell_fees_and_taxes_reduce_realized_profit():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="sell-1",
                transaction_date="2026-02-10",
                transaction_type="sell",
                quantity=4,
                price=70,
                fee=5,
                tax=3,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.realized_profit_loss == pytest.approx(72)
    assert position.total_sell_fees == pytest.approx(5)
    assert position.total_sell_taxes == pytest.approx(3)


def test_complete_sale_closes_cost_basis():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="sell-1",
                transaction_date="2026-02-10",
                transaction_type="sell",
                quantity=10,
                price=60,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(0)
    assert position.cost_basis == pytest.approx(0)
    assert position.average_cost == pytest.approx(0)
    assert position.realized_profit_loss == pytest.approx(100)


def test_sell_more_than_owned_is_rejected():
    with pytest.raises(
        PortfolioCalculationError,
        match="cannot sell more shares than owned",
    ):
        build_portfolio_snapshot_from_transactions(
            transactions=(
                transaction(
                    external_id="buy-1",
                    transaction_date="2026-01-10",
                    transaction_type="buy",
                    quantity=10,
                    price=50,
                ),
                transaction(
                    external_id="sell-1",
                    transaction_date="2026-02-10",
                    transaction_type="sell",
                    quantity=11,
                    price=60,
                ),
            ),
        )


def test_sell_without_position_is_rejected():
    with pytest.raises(
        PortfolioCalculationError,
    ):
        build_portfolio_snapshot_from_transactions(
            transactions=(
                transaction(
                    external_id="sell-1",
                    transaction_date="2026-01-10",
                    transaction_type="sell",
                    quantity=1,
                    price=60,
                ),
            ),
        )


def test_dividend_does_not_change_position_cost():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="dividend-1",
                transaction_date="2026-02-10",
                transaction_type="dividend",
                company_id=1,
                amount=25,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(10)
    assert position.cost_basis == pytest.approx(500)
    assert position.realized_profit_loss == pytest.approx(0)


def test_cash_does_not_create_position():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="cash-1",
                transaction_date="2026-01-01",
                transaction_type="cash",
                company_id=None,
                amount=1000,
            ),
        ),
    )

    assert snapshot.positions == ()


def test_as_of_date_excludes_future_transactions():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="sell-1",
                transaction_date="2026-03-10",
                transaction_type="sell",
                quantity=5,
                price=70,
            ),
        ),
        as_of_date=date(2026, 2, 1),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(10)
    assert position.realized_profit_loss == pytest.approx(0)


def test_multiple_companies_are_separate_positions():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                company_id=1,
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="buy-2",
                transaction_date="2026-01-11",
                transaction_type="buy",
                company_id=2,
                quantity=5,
                price=100,
            ),
        ),
    )

    assert len(snapshot.positions) == 2

    assert snapshot.positions[0].company_id == 1
    assert snapshot.positions[0].quantity == pytest.approx(10)

    assert snapshot.positions[1].company_id == 2
    assert snapshot.positions[1].quantity == pytest.approx(5)


def test_position_rejects_mixed_currencies():
    with pytest.raises(
        PortfolioCalculationError,
        match="same currency",
    ):
        build_portfolio_snapshot_from_transactions(
            transactions=(
                transaction(
                    external_id="buy-1",
                    transaction_date="2026-01-10",
                    transaction_type="buy",
                    quantity=10,
                    price=50,
                    currency="EUR",
                ),
                transaction(
                    external_id="buy-2",
                    transaction_date="2026-02-10",
                    transaction_type="buy",
                    quantity=5,
                    price=60,
                    currency="USD",
                ),
            ),
        )


def test_repository_snapshot_respects_as_of_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_portfolio_transaction(
            connection,
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                company_id=company_id,
                quantity=10,
                price=50,
            ),
        )

        insert_portfolio_transaction(
            connection,
            transaction(
                external_id="sell-1",
                transaction_date="2026-03-10",
                transaction_type="sell",
                company_id=company_id,
                quantity=4,
                price=70,
            ),
        )

        snapshot = build_portfolio_snapshot(
            connection=connection,
            as_of_date=date(2026, 2, 1),
        )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(10)
    assert position.cost_basis == pytest.approx(500)
    assert position.realized_profit_loss == pytest.approx(0)


def test_transactions_are_processed_chronologically():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="sell-1",
                transaction_date="2026-03-10",
                transaction_type="sell",
                quantity=5,
                price=70,
            ),
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(5)
    assert position.cost_basis == pytest.approx(250)
    assert position.realized_profit_loss == pytest.approx(100)


def test_new_buy_after_partial_sale_uses_remaining_cost():
    snapshot = build_portfolio_snapshot_from_transactions(
        transactions=(
            transaction(
                external_id="buy-1",
                transaction_date="2026-01-10",
                transaction_type="buy",
                quantity=10,
                price=50,
            ),
            transaction(
                external_id="sell-1",
                transaction_date="2026-02-10",
                transaction_type="sell",
                quantity=5,
                price=70,
            ),
            transaction(
                external_id="buy-2",
                transaction_date="2026-03-10",
                transaction_type="buy",
                quantity=5,
                price=100,
            ),
        ),
    )

    position = snapshot.positions[0]

    assert position.quantity == pytest.approx(10)
    assert position.cost_basis == pytest.approx(750)
    assert position.average_cost == pytest.approx(75)
    assert position.realized_profit_loss == pytest.approx(100)