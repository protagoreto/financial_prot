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

def get_price_on_or_before(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> PriceRecord | None:
    row = connection.execute(
        """
        SELECT
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
        FROM prices
        WHERE company_id = ?
        AND price_date <= ?
        ORDER BY price_date DESC
        LIMIT 1
        """,
        (
            company_id,
            as_of_date.isoformat(),
        ),
    ).fetchone()

    if row is None:
        return None

    return PriceRecord(
        company_id=row["company_id"],
        price_date=row["price_date"],
        open=row["open"],
        high=row["high"],
        low=row["low"],
        close=row["close"],
        adjusted_close=row["adjusted_close"],
        volume=row["volume"],
        currency=row["currency"],
        source_id=row["source_id"],
    )

def get_latest_financial_on_or_before(
    connection: sqlite3.Connection,
    company_id: int,
    metric: FinancialMetric,
    as_of_date: date,
    period_type: PeriodType,
) -> FinancialRecord | None:
    row = connection.execute(
        """
        SELECT
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
        FROM financials
        WHERE company_id = ?
        AND metric = ?
        AND period_type = ?
        AND publication_date IS NOT NULL
        AND publication_date <= ?
        ORDER BY publication_date DESC, period_end DESC
        LIMIT 1
        """,
        (
            company_id,
            metric.value,
            period_type.value,
            as_of_date.isoformat(),
        ),
    ).fetchone()

    if row is None:
        return None

    return FinancialRecord(
        company_id=row["company_id"],
        statement_type=row["statement_type"],
        metric=row["metric"],
        value=row["value"],
        currency=row["currency"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        period_type=row["period_type"],
        publication_date=row["publication_date"],
        source_id=row["source_id"],
    )

def get_latest_estimate_on_or_before(
    connection: sqlite3.Connection,
    company_id: int,
    metric: FinancialMetric,
    fiscal_period_end: date,
    as_of_date: date,
) -> EstimateRecord | None:
    row = connection.execute(
        """
        SELECT
            company_id,
            metric,
            value,
            currency,
            fiscal_period_end,
            estimate_date,
            analyst_count,
            source_id
        FROM estimates
        WHERE company_id = ?
        AND metric = ?
        AND fiscal_period_end = ?
        AND estimate_date <= ?
        ORDER BY estimate_date DESC
        LIMIT 1
        """,
        (
            company_id,
            metric.value,
            fiscal_period_end.isoformat(),
            as_of_date.isoformat(),
        ),
    ).fetchone()

    if row is None:
        return None

    return EstimateRecord(
        company_id=row["company_id"],
        metric=row["metric"],
        value=row["value"],
        currency=row["currency"],
        fiscal_period_end=row["fiscal_period_end"],
        estimate_date=row["estimate_date"],
        analyst_count=row["analyst_count"],
        source_id=row["source_id"],
    )