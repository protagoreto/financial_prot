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