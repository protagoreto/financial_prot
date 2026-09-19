import sqlite3

from src.models import EstimateRecord, FinancialRecord, PriceRecord

def insert_financial_record(
    connection: sqlite3.Connection,
    record: FinancialRecord,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO financials (
            company_id,
            statement_type,
            metric,
            value,
            currency,
            period_start,
            period_end,
            period_type,
            publication_date,
            source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.company_id,
            record.statement_type.value,
            record.metric.value,
            record.value,
            record.currency,
            record.period_start.isoformat()
            if record.period_start
            else None,
            record.period_end.isoformat(),
            record.period_type.value,
            record.publication_date.isoformat()
            if record.publication_date
            else None,
            record.source_id,
        ),
    )

    connection.commit()
    return cursor.lastrowid


def insert_estimate_record(
    connection: sqlite3.Connection,
    record: EstimateRecord,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO estimates (
            company_id,
            metric,
            value,
            currency,
            fiscal_period_end,
            estimate_date,
            analyst_count,
            source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.company_id,
            record.metric.value,
            record.value,
            record.currency,
            record.fiscal_period_end.isoformat(),
            record.estimate_date.isoformat(),
            record.analyst_count,
            record.source_id,
        ),
    )

    connection.commit()
    return cursor.lastrowid


def insert_price_record(
    connection: sqlite3.Connection,
    record: PriceRecord,
) -> int:
    connection.execute(
        """
        INSERT INTO prices (
            company_id,
            price_date,
            open,
            high,
            low,
            close,
            adjusted_close,
            volume,
            currency,
            source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(company_id, price_date)
        DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            adjusted_close = excluded.adjusted_close,
            volume = excluded.volume,
            currency = excluded.currency,
            source_id = excluded.source_id
        """,
        (
            record.company_id,
            record.price_date.isoformat(),
            record.open,
            record.high,
            record.low,
            record.close,
            record.adjusted_close,
            record.volume,
            record.currency,
            record.source_id,
        ),
    )

    row = connection.execute(
        """
        SELECT price_id
        FROM prices
        WHERE company_id = ?
        AND price_date = ?
        """,
        (
            record.company_id,
            record.price_date.isoformat(),
        ),
    ).fetchone()

    connection.commit()

    return row["price_id"]

from datetime import date


def get_latest_price_date(
    connection: sqlite3.Connection,
    company_id: int,
) -> date | None:
    row = connection.execute(
        """
        SELECT MAX(price_date) AS latest_price_date
        FROM prices
        WHERE company_id = ?
        """,
        (company_id,),
    ).fetchone()

    if row is None or row["latest_price_date"] is None:
        return None

    return date.fromisoformat(
        row["latest_price_date"]
    )