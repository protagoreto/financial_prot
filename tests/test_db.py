from pathlib import Path

from src.db import connect, initialize_database


def test_database_initializes(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    expected_tables = {
        "schema_meta",
	"portfolio_transactions",
        "companies",
        "sources",
        "prices",
        "financials",
        "estimates",
        "dividends",
        "analysis_runs",
    }

    assert expected_tables.issubset(tables)


def test_schema_version(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = 'schema_version'
            """
        ).fetchone()

    assert row["value"] == "0.5.0"


def test_foreign_keys_are_enabled(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        row = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()

    assert row[0] == 1


def test_financial_tables_have_expected_indexes(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        indexes = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                AND name NOT LIKE 'sqlite_%'
                """
            )
        }

    expected_indexes = {
        "idx_prices_company_date",
	"idx_portfolio_transactions_date",
	"idx_portfolio_transactions_company_date",
        "idx_financials_company_period",
        "idx_estimates_company_date",
        "idx_dividends_company_date",
    }

    assert expected_indexes.issubset(indexes)

def test_publication_dates_table_exists(tmp_path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'publication_dates'
            """
        ).fetchone()

    assert row is not None


def test_schema_version_is_0_5_0(tmp_path):
    db_path = tmp_path / "test.sqlite"

    initialize_database(db_path)

    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = 'schema_version'
            """
        ).fetchone()

    assert row is not None
    assert row["value"] == "0.5.0"