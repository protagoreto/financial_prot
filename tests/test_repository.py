from pathlib import Path

from src.db import connect, initialize_database
from src.models import EstimateRecord, FinancialRecord, PriceRecord
from src.repository import (
    insert_estimate_record,
    insert_financial_record,
    insert_price_record,
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
            "TESTEX",
            "EUR",
        ),
    )

    connection.commit()
    return cursor.lastrowid


def test_insert_financial_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = FinancialRecord(
            company_id=company_id,
            statement_type="income_statement",
            metric="net_income",
            value=100.0,
            currency="EUR",
            period_start="2025-01-01",
            period_end="2025-12-31",
            period_type="annual",
            publication_date="2026-02-01",
        )

        record_id = insert_financial_record(connection, record)

        row = connection.execute(
            """
            SELECT *
            FROM financials
            WHERE financial_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["metric"] == "net_income"
    assert row["value"] == 100.0
    assert row["period_end"] == "2025-12-31"


def test_insert_estimate_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = EstimateRecord(
            company_id=company_id,
            metric="eps",
            value=2.50,
            currency="EUR",
            fiscal_period_end="2027-12-31",
            estimate_date="2026-09-19",
            analyst_count=12,
        )

        record_id = insert_estimate_record(connection, record)

        row = connection.execute(
            """
            SELECT *
            FROM estimates
            WHERE estimate_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["metric"] == "eps"
    assert row["value"] == 2.50
    assert row["estimate_date"] == "2026-09-19"
    assert row["analyst_count"] == 12

def test_insert_price_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.74,
            adjusted_close=51.74,
            volume=6017239,
            currency="EUR",
        )

        record_id = insert_price_record(
            connection,
            record,
        )

        row = connection.execute(
            """
            SELECT *
            FROM prices
            WHERE price_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["price_date"] == "2026-09-18"
    assert row["close"] == 51.74
    assert row["adjusted_close"] == 51.74
    assert row["volume"] == 6017239
    assert row["currency"] == "EUR"

def test_insert_price_record_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        first_record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.74,
            adjusted_close=51.74,
            volume=6017239,
            currency="EUR",
        )

        first_id = insert_price_record(
            connection,
            first_record,
        )

        updated_record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.75,
            adjusted_close=51.75,
            volume=6018000,
            currency="EUR",
        )

        second_id = insert_price_record(
            connection,
            updated_record,
        )

        rows = connection.execute(
            """
            SELECT *
            FROM prices
            WHERE company_id = ?
            AND price_date = ?
            """,
            (
                company_id,
                "2026-09-18",
            ),
        ).fetchall()

    assert first_id == second_id
    assert len(rows) == 1
    assert rows[0]["close"] == 51.75
    assert rows[0]["volume"] == 6018000

def test_get_latest_price_date_returns_none_without_prices(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        from src.repository import get_latest_price_date

        latest = get_latest_price_date(
            connection,
            company_id,
        )

    assert latest is None


def test_get_latest_price_date_returns_most_recent_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-17",
                close=50.0,
                currency="EUR",
            ),
        )

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-18",
                close=51.0,
                currency="EUR",
            ),
        )

        from src.repository import get_latest_price_date

        latest = get_latest_price_date(
            connection,
            company_id,
        )

    assert latest.isoformat() == "2026-09-18"