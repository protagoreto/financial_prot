from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.models import (
    PortfolioTransaction,
    PriceRecord,
)
from src.portfolio import (
    PortfolioCalculationError,
    build_valued_portfolio_snapshot,
)
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


def test_position_uses_price_on_or_before_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            external_id="cash-1",
            transaction_date="2026-01-01",
            transaction_type="cash",
            amount=1000,
        )

        add_transaction(
            connection,
            external_id="buy-1",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_price(
            connection,
            company_id=company_id,
            price_date="2026-02-01",
            close=60,
        )

        add_price(
            connection,
            company_id=company_id,
            price_date="2026-03-01",
            close=80,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection=connection,
            as_of_date=date(2026, 2, 15),
        )

    position = snapshot.positions[0]

    assert position.price == pytest.approx(60)
    assert position.price_date == date(2026, 2, 1)
    assert position.market_value == pytest.approx(600)


def test_unrealized_profit_loss_and_return(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            external_id="cash-1",
            transaction_date="2026-01-01",
            transaction_type="cash",
            amount=1000,
        )

        add_transaction(
            connection,
            external_id="buy-1",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=company_id,
            quantity=10,
            price=50,
        )

        add_price(
            connection,
            company_id=company_id,
            price_date="2026-02-01",
            close=60,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    position = snapshot.positions[0]

    assert position.cost_basis == pytest.approx(500)
    assert position.market_value == pytest.approx(600)
    assert position.unrealized_profit_loss == pytest.approx(100)
    assert position.unrealized_return == pytest.approx(0.20)


def test_cash_reflects_buy_cash_flow(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

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

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]

    assert summary.cash == pytest.approx(500)
    assert summary.positions_market_value == pytest.approx(600)
    assert summary.total_value == pytest.approx(1100)


def test_buy_fees_reduce_cash(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_id,
            quantity=10,
            price=50,
            fee=5,
            tax=2,
        )

        add_price(
            connection,
            company_id,
            "2026-02-01",
            60,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]

    assert summary.cash == pytest.approx(493)
    assert snapshot.positions[0].cost_basis == pytest.approx(507)


def test_sell_increases_cash(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

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
            fee=5,
            tax=3,
        )

        add_price(
            connection,
            company_id,
            "2026-02-10",
            65,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]
    position = snapshot.positions[0]

    assert summary.cash == pytest.approx(772)
    assert position.quantity == pytest.approx(6)
    assert position.realized_profit_loss == pytest.approx(72)


def test_dividend_increases_cash_net_of_costs(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=100,
        )

        add_transaction(
            connection,
            "dividend-1",
            "2026-02-01",
            "dividend",
            company_id=company_id,
            amount=25,
            tax=5,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]

    assert summary.cash == pytest.approx(120)
    assert summary.positions_market_value == pytest.approx(0)
    assert summary.total_value == pytest.approx(120)


def test_standalone_fee_and_tax_reduce_cash(
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
            amount=100,
        )

        add_transaction(
            connection,
            "fee-1",
            "2026-01-02",
            "fee",
            amount=5,
        )

        add_transaction(
            connection,
            "tax-1",
            "2026-01-03",
            "tax",
            amount=3,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]

    assert summary.cash == pytest.approx(92)


def test_weight_includes_cash(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

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

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    position = snapshot.positions[0]

    assert position.market_value == pytest.approx(600)
    assert position.weight == pytest.approx(600 / 1100)


def test_two_positions_have_correct_weights(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_1 = create_company(
            connection,
            name="Company One",
            ticker="ONE",
        )
        company_2 = create_company(
            connection,
            name="Company Two",
            ticker="TWO",
        )

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

        add_transaction(
            connection,
            "buy-1",
            "2026-01-10",
            "buy",
            company_id=company_1,
            quantity=5,
            price=40,
        )

        add_transaction(
            connection,
            "buy-2",
            "2026-01-10",
            "buy",
            company_id=company_2,
            quantity=5,
            price=60,
        )

        add_price(
            connection,
            company_1,
            "2026-02-01",
            40,
        )

        add_price(
            connection,
            company_2,
            "2026-02-01",
            60,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    assert snapshot.currency_summaries[0].total_value == pytest.approx(
        1000
    )

    assert snapshot.positions[0].weight == pytest.approx(0.20)
    assert snapshot.positions[1].weight == pytest.approx(0.30)


def test_missing_price_is_rejected(
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

        with pytest.raises(
            PortfolioCalculationError,
            match="missing price",
        ):
            build_valued_portfolio_snapshot(
                connection,
                date(2026, 2, 15),
            )


def test_future_price_is_not_used(
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
            "2026-03-01",
            80,
        )

        with pytest.raises(
            PortfolioCalculationError,
            match="missing price",
        ):
            build_valued_portfolio_snapshot(
                connection,
                date(2026, 2, 15),
            )


def test_price_currency_must_match_position_currency(
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
            currency="EUR",
        )

        add_price(
            connection,
            company_id,
            "2026-02-01",
            60,
            currency="USD",
        )

        with pytest.raises(
            PortfolioCalculationError,
            match="currency",
        ):
            build_valued_portfolio_snapshot(
                connection,
                date(2026, 2, 15),
            )


def test_currencies_are_not_combined(
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
            "eur-cash",
            "2026-01-01",
            "cash",
            currency="EUR",
            amount=1000,
        )

        add_transaction(
            connection,
            "usd-cash",
            "2026-01-01",
            "cash",
            currency="USD",
            amount=2000,
        )

        add_transaction(
            connection,
            "eur-buy",
            "2026-01-10",
            "buy",
            currency="EUR",
            company_id=company_eur,
            quantity=10,
            price=50,
        )

        add_transaction(
            connection,
            "usd-buy",
            "2026-01-10",
            "buy",
            currency="USD",
            company_id=company_usd,
            quantity=10,
            price=100,
        )

        add_price(
            connection,
            company_eur,
            "2026-02-01",
            60,
            currency="EUR",
        )

        add_price(
            connection,
            company_usd,
            "2026-02-01",
            120,
            currency="USD",
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    assert len(snapshot.currency_summaries) == 2

    summaries = {
        summary.currency: summary
        for summary in snapshot.currency_summaries
    }

    assert summaries["EUR"].cash == pytest.approx(500)
    assert summaries["EUR"].positions_market_value == pytest.approx(600)
    assert summaries["EUR"].total_value == pytest.approx(1100)

    assert summaries["USD"].cash == pytest.approx(1000)
    assert summaries["USD"].positions_market_value == pytest.approx(1200)
    assert summaries["USD"].total_value == pytest.approx(2200)


def test_closed_position_not_in_valued_positions(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        add_transaction(
            connection,
            "cash-1",
            "2026-01-01",
            "cash",
            amount=1000,
        )

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

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    assert snapshot.positions == ()
    assert snapshot.currency_summaries[0].cash == pytest.approx(1100)


def test_as_of_date_excludes_future_cash_flow(
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
            amount=1000,
        )

        add_transaction(
            connection,
            "cash-future",
            "2026-03-01",
            "cash",
            amount=500,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection,
            date(2026, 2, 15),
        )

    assert snapshot.currency_summaries[0].cash == pytest.approx(1000)

def test_currency_summary_value_identity(
    connection,
):
    company_id = insert_company(
        connection,
        ticker="TEST",
        exchange="BME",
        currency="EUR",
    )

    insert_portfolio_transaction(
        connection,
        PortfolioTransaction(
            external_id="cash-identity",
            transaction_date="2026-01-01",
            transaction_type="cash",
            currency="EUR",
            amount=1000.0,
        ),
    )

    insert_portfolio_transaction(
        connection,
        PortfolioTransaction(
            external_id="buy-identity",
            transaction_date="2026-01-02",
            transaction_type="buy",
            currency="EUR",
            company_id=company_id,
            quantity=10.0,
            price=50.0,
        ),
    )

    insert_price_record(
        connection,
        PriceRecord(
            company_id=company_id,
            price_date="2026-02-01",
            close=60.0,
            currency="EUR",
            source_id=1,
        ),
    )

    snapshot = build_valued_portfolio_snapshot(
        connection=connection,
        as_of_date=date(2026, 2, 15),
    )

    summary = snapshot.currency_summaries[0]

    assert summary.total_value == pytest.approx(
        summary.positions_market_value
        + summary.cash
    )


def test_position_weights_use_total_value_including_cash(
    connection,
):
    company_id = insert_company(
        connection,
        ticker="WEIGHT",
        exchange="BME",
        currency="EUR",
    )

    insert_portfolio_transaction(
        connection,
        PortfolioTransaction(
            external_id="cash-weight",
            transaction_date="2026-01-01",
            transaction_type="cash",
            currency="EUR",
            amount=1000.0,
        ),
    )

    insert_portfolio_transaction(
        connection,
        PortfolioTransaction(
            external_id="buy-weight",
            transaction_date="2026-01-02",
            transaction_type="buy",
            currency="EUR",
            company_id=company_id,
            quantity=10.0,
            price=50.0,
        ),
    )

    insert_price_record(
        connection,
        PriceRecord(
            company_id=company_id,
            price_date="2026-02-01",
            close=60.0,
            currency="EUR",
            source_id=1,
        ),
    )

    snapshot = build_valued_portfolio_snapshot(
        connection=connection,
        as_of_date=date(2026, 2, 15),
    )

    position = snapshot.positions[0]
    summary = snapshot.currency_summaries[0]

    assert position.weight == pytest.approx(
        position.market_value
        / summary.total_value
    )


def test_currency_summary_value_identity(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(
            connection,
            ticker="IDENTITY",
        )

        add_transaction(
            connection,
            external_id="cash-identity",
            transaction_date="2026-01-01",
            transaction_type="cash",
            amount=1000.0,
        )

        add_transaction(
            connection,
            external_id="buy-identity",
            transaction_date="2026-01-02",
            transaction_type="buy",
            company_id=company_id,
            quantity=10.0,
            price=50.0,
        )

        add_price(
            connection,
            company_id=company_id,
            price_date="2026-02-01",
            close=60.0,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection=connection,
            as_of_date=date(2026, 2, 15),
        )

    summary = snapshot.currency_summaries[0]

    assert summary.positions_market_value == pytest.approx(
        600.0
    )
    assert summary.cash == pytest.approx(500.0)
    assert summary.total_value == pytest.approx(1100.0)

    assert summary.total_value == pytest.approx(
        summary.positions_market_value
        + summary.cash
    )


def test_position_weights_use_total_value_including_cash(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(
            connection,
            ticker="WEIGHT",
        )

        add_transaction(
            connection,
            external_id="cash-weight",
            transaction_date="2026-01-01",
            transaction_type="cash",
            amount=1000.0,
        )

        add_transaction(
            connection,
            external_id="buy-weight",
            transaction_date="2026-01-02",
            transaction_type="buy",
            company_id=company_id,
            quantity=10.0,
            price=50.0,
        )

        add_price(
            connection,
            company_id=company_id,
            price_date="2026-02-01",
            close=60.0,
        )

        snapshot = build_valued_portfolio_snapshot(
            connection=connection,
            as_of_date=date(2026, 2, 15),
        )

    position = snapshot.positions[0]
    summary = snapshot.currency_summaries[0]

    assert position.market_value == pytest.approx(600.0)
    assert summary.total_value == pytest.approx(1100.0)

    assert position.weight == pytest.approx(
        600.0 / 1100.0
    )

    assert position.weight == pytest.approx(
        position.market_value
        / summary.total_value
    )