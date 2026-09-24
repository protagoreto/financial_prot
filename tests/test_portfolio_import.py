from pathlib import Path

import pytest

from src.db import connect, managed_connection, initialize_database
from src.portfolio_import import (
    PortfolioImportError,
    import_portfolio_csv,
)
from src.repository import (
    get_company_id_by_ticker_exchange,
    get_portfolio_transactions,
)


HEADER = (
    "external_id,transaction_date,transaction_type,"
    "currency,ticker,exchange,quantity,price,"
    "amount,fee,tax,note\n"
)


def create_company(
    connection,
    name: str = "Test Company",
    ticker: str = "TEST",
    exchange: str = "BME",
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
            exchange,
            currency,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def write_csv(
    path: Path,
    rows: str,
) -> None:
    path.write_text(
        HEADER + rows,
        encoding="utf-8",
    )


def test_company_lookup_by_ticker_and_exchange(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = create_company(
            connection,
            ticker="ITX",
            exchange="BME",
        )

        result = get_company_id_by_ticker_exchange(
            connection,
            ticker="itx",
            exchange="bme",
        )

    assert result == company_id


def test_company_lookup_returns_none_when_unknown(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        result = get_company_id_by_ticker_exchange(
            connection,
            ticker="UNKNOWN",
            exchange="BME",
        )

    assert result is None


def test_import_buy_transaction(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "TEST,BME,10,50,,1,2,initial buy\n"
        ),
    )

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        result = import_portfolio_csv(
            connection,
            csv_path,
        )

        transactions = get_portfolio_transactions(
            connection
        )

    assert result.rows_read == 1
    assert result.transactions_processed == 1
    assert len(transactions) == 1

    transaction = transactions[0]

    assert transaction.company_id == company_id
    assert transaction.quantity == pytest.approx(10)
    assert transaction.price == pytest.approx(50)
    assert transaction.fee == pytest.approx(1)
    assert transaction.tax == pytest.approx(2)
    assert transaction.note == "initial buy"


def test_import_cash_without_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "cash-1,2026-01-01,cash,EUR,"
            ",,,,1000,0,0,deposit\n"
        ),
    )

    with managed_connection(db_path) as connection:
        result = import_portfolio_csv(
            connection,
            csv_path,
        )

        transactions = get_portfolio_transactions(
            connection
        )

    assert result.transactions_processed == 1
    assert transactions[0].company_id is None
    assert transactions[0].amount == pytest.approx(1000)


def test_import_dividend(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "div-1,2026-02-01,dividend,EUR,"
            "TEST,BME,,,100,2,19,dividend\n"
        ),
    )

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        import_portfolio_csv(
            connection,
            csv_path,
        )

        transaction = get_portfolio_transactions(
            connection
        )[0]

    assert transaction.company_id == company_id
    assert transaction.amount == pytest.approx(100)
    assert transaction.fee == pytest.approx(2)
    assert transaction.tax == pytest.approx(19)


def test_import_is_idempotent_by_external_id(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "TEST,BME,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        create_company(connection)

        import_portfolio_csv(
            connection,
            csv_path,
        )

        import_portfolio_csv(
            connection,
            csv_path,
        )

        transactions = get_portfolio_transactions(
            connection
        )

    assert len(transactions) == 1


def test_unknown_company_is_rejected(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "UNKNOWN,BME,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        with pytest.raises(
            PortfolioImportError,
            match="unknown company",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_buy_requires_company_identity(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            ",,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        with pytest.raises(
            PortfolioImportError,
            match="ticker and exchange are required",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_partial_company_identity_is_rejected(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "TEST,,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        with pytest.raises(
            PortfolioImportError,
            match="must be provided together",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_cash_cannot_reference_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "cash-1,2026-01-01,cash,EUR,"
            "TEST,BME,,,1000,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        create_company(connection)

        with pytest.raises(
            PortfolioImportError,
            match="cannot reference a company",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_invalid_numeric_value_is_rejected(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "TEST,BME,ten,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        create_company(connection)

        with pytest.raises(
            PortfolioImportError,
            match="quantity must be numeric",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_missing_required_column_is_rejected(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    csv_path.write_text(
        (
            "external_id,transaction_date,"
            "transaction_type,currency\n"
            "cash-1,2026-01-01,cash,EUR\n"
        ),
        encoding="utf-8",
    )

    with managed_connection(db_path) as connection:
        with pytest.raises(
            PortfolioImportError,
            match="missing columns",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )


def test_invalid_row_does_not_partially_import_file(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,buy,EUR,"
            "TEST,BME,10,50,,0,0,\n"
            "buy-2,2026-01-11,buy,EUR,"
            "UNKNOWN,BME,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        create_company(connection)

        with pytest.raises(
            PortfolioImportError,
            match="unknown company",
        ):
            import_portfolio_csv(
                connection,
                csv_path,
            )

        transactions = get_portfolio_transactions(
            connection
        )

    assert transactions == ()


def test_transaction_type_is_case_insensitive(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    csv_path = tmp_path / "portfolio.csv"
    initialize_database(db_path)

    write_csv(
        csv_path,
        (
            "buy-1,2026-01-10,BUY,eur,"
            "test,bme,10,50,,0,0,\n"
        ),
    )

    with managed_connection(db_path) as connection:
        company_id = create_company(connection)

        import_portfolio_csv(
            connection,
            csv_path,
        )

        transaction = get_portfolio_transactions(
            connection
        )[0]

    assert transaction.company_id == company_id
    assert transaction.currency == "EUR"