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
	"portfolio_theses",
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

    assert row["value"] == "0.7.0"


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
	"idx_portfolio_theses_company_date",
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


def test_existing_database_adds_fundamental_profile(
    tmp_path: Path,
):
    db_path = tmp_path / "legacy.sqlite"

    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE companies (
                company_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT,
                isin TEXT,
                country TEXT,
                sector TEXT,
                industry TEXT,
                currency TEXT,
                exchange TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, exchange)
            );

            INSERT INTO schema_meta(key, value)
            VALUES ('schema_version', '0.5.0');

            INSERT INTO companies (
                name,
                ticker,
                exchange,
                currency
            )
            VALUES (
                'Legacy Company',
                'LEG',
                'BME',
                'EUR'
            );
            """
        )

    initialize_database(db_path)
    initialize_database(db_path)

    with connect(db_path) as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(companies)"
            )
        }

        company = connection.execute(
            """
            SELECT fundamental_profile
            FROM companies
            WHERE ticker = 'LEG'
            """
        ).fetchone()

        version = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = 'schema_version'
            """
        ).fetchone()

    assert "fundamental_profile" in columns
    assert "symbol" in columns
    assert company["fundamental_profile"] == "operating"
    assert version["value"] == "0.7.0"


def test_fundamental_profile_constraint(
    tmp_path: Path,
):
    import sqlite3

    import pytest

    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO companies (
                    name,
                    ticker,
                    exchange,
                    currency,
                    fundamental_profile
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Invalid Profile",
                    "BAD",
                    "BME",
                    "EUR",
                    "unknown",
                ),
            )



def test_existing_database_adds_symbol_idempotently(
    tmp_path: Path,
):
    db_path = tmp_path / "legacy_symbol.sqlite"

    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE companies (
                company_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT,
                isin TEXT,
                country TEXT,
                sector TEXT,
                industry TEXT,
                fundamental_profile TEXT NOT NULL
                    DEFAULT 'operating',
                currency TEXT,
                exchange TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, exchange)
            );

            INSERT INTO schema_meta(key, value)
            VALUES ('schema_version', '0.6.0');

            INSERT INTO companies (
                name,
                ticker,
                exchange,
                currency
            )
            VALUES (
                'Legacy Company',
                'LEG',
                'BME',
                'EUR'
            );
            """
        )

    initialize_database(db_path)
    initialize_database(db_path)

    with connect(db_path) as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(companies)"
            )
        }

        company = connection.execute(
            """
            SELECT symbol
            FROM companies
            WHERE ticker = 'LEG'
            """
        ).fetchone()

        version = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key = 'schema_version'
            """
        ).fetchone()

    assert "symbol" in columns
    assert company["symbol"] is None
    assert version["value"] == "0.7.0"
