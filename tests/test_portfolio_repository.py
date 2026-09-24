from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.db import connect, managed_connection, initialize_database
from src.models import (
    PortfolioTransaction,
    PortfolioTransactionType,
)
from src.repository import (
    get_portfolio_transactions,
    insert_portfolio_transaction,
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


def test_buy_transaction_is_valid():
    transaction = PortfolioTransaction(
        external_id="buy-001",
        transaction_date="2026-01-10",
        transaction_type=(
            PortfolioTransactionType.BUY
        ),
        company_id=1,
        quantity=10,
        price=50,
        fee=2,
        currency="EUR",
    )

    assert transaction.quantity == 10
    assert transaction.price == 50
    assert transaction.fee == 2


def test_buy_requires_company():
    with pytest.raises(ValidationError):
        PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            quantity=10,
            price=50,
            currency="EUR",
        )


def test_buy_requires_quantity_and_price():
    with pytest.raises(ValidationError):
        PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=1,
            currency="EUR",
        )


def test_buy_rejects_explicit_amount():
    with pytest.raises(ValidationError):
        PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=1,
            quantity=10,
            price=50,
            amount=500,
            currency="EUR",
        )


def test_dividend_requires_positive_amount():
    with pytest.raises(ValidationError):
        PortfolioTransaction(
            external_id="dividend-001",
            transaction_date="2026-02-01",
            transaction_type="dividend",
            company_id=1,
            amount=-20,
            currency="EUR",
        )


def test_cash_can_be_negative():
    transaction = PortfolioTransaction(
        external_id="cash-001",
        transaction_date="2026-02-01",
        transaction_type="cash",
        amount=-100,
        currency="EUR",
    )

    assert transaction.amount == -100


def test_cash_cannot_reference_company():
    with pytest.raises(ValidationError):
        PortfolioTransaction(
            external_id="cash-001",
            transaction_date="2026-02-01",
            transaction_type="cash",
            company_id=1,
            amount=100,
            currency="EUR",
        )


def test_insert_portfolio_transaction(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        transaction = PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=company_id,
            quantity=10,
            price=50,
            fee=2,
            currency="EUR",
        )

        transaction_id = (
            insert_portfolio_transaction(
                connection,
                transaction,
            )
        )

        row = connection.execute(
            """
            SELECT *
            FROM portfolio_transactions
            WHERE transaction_id = ?
            """,
            (transaction_id,),
        ).fetchone()

    assert row["external_id"] == "buy-001"
    assert row["transaction_type"] == "buy"
    assert row["quantity"] == 10
    assert row["price"] == 50
    assert row["fee"] == 2
    assert row["currency"] == "EUR"


def test_insert_is_idempotent(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        transaction = PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=company_id,
            quantity=10,
            price=50,
            currency="EUR",
        )

        first_id = insert_portfolio_transaction(
            connection,
            transaction,
        )

        second_id = insert_portfolio_transaction(
            connection,
            transaction,
        )

        count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM portfolio_transactions
            """
        ).fetchone()["count"]

    assert first_id == second_id
    assert count == 1


def test_transactions_are_chronological(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_portfolio_transaction(
            connection,
            PortfolioTransaction(
                external_id="sell-001",
                transaction_date="2026-03-01",
                transaction_type="sell",
                company_id=company_id,
                quantity=2,
                price=60,
                currency="EUR",
            ),
        )

        insert_portfolio_transaction(
            connection,
            PortfolioTransaction(
                external_id="buy-001",
                transaction_date="2026-01-10",
                transaction_type="buy",
                company_id=company_id,
                quantity=10,
                price=50,
                currency="EUR",
            ),
        )

        transactions = (
            get_portfolio_transactions(
                connection
            )
        )

    assert [
        transaction.external_id
        for transaction in transactions
    ] == [
        "buy-001",
        "sell-001",
    ]


def test_transactions_respect_as_of_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        insert_portfolio_transaction(
            connection,
            PortfolioTransaction(
                external_id="buy-001",
                transaction_date="2026-01-10",
                transaction_type="buy",
                company_id=company_id,
                quantity=10,
                price=50,
                currency="EUR",
            ),
        )

        insert_portfolio_transaction(
            connection,
            PortfolioTransaction(
                external_id="sell-001",
                transaction_date="2026-03-01",
                transaction_type="sell",
                company_id=company_id,
                quantity=2,
                price=60,
                currency="EUR",
            ),
        )

        transactions = (
            get_portfolio_transactions(
                connection=connection,
                as_of_date=date(
                    2026,
                    2,
                    1,
                ),
            )
        )

    assert len(transactions) == 1
    assert (
        transactions[0].external_id
        == "buy-001"
    )


def test_foreign_key_rejects_unknown_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        transaction = PortfolioTransaction(
            external_id="buy-001",
            transaction_date="2026-01-10",
            transaction_type="buy",
            company_id=999,
            quantity=10,
            price=50,
            currency="EUR",
        )

        with pytest.raises(Exception):
            insert_portfolio_transaction(
                connection,
                transaction,
            )