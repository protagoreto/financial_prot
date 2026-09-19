from datetime import date, datetime, timedelta, timezone
import sqlite3

from src.models import PriceRecord
from src.providers.base import PriceProvider
from src.repository import get_latest_price_date, insert_price_record


def get_or_create_company(
    connection: sqlite3.Connection,
    name: str,
    ticker: str,
    exchange: str,
    currency: str,
) -> int:
    row = connection.execute(
        """
        SELECT company_id
        FROM companies
        WHERE ticker = ?
        AND exchange = ?
        """,
        (ticker, exchange),
    ).fetchone()

    if row:
        return row["company_id"]

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


def create_source(
    connection: sqlite3.Connection,
    provider: str,
    document_type: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO sources (
            provider,
            retrieved_at,
            document_type,
            confidence
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            provider,
            datetime.now(timezone.utc).isoformat(),
            document_type,
            "secondary",
        ),
    )

    connection.commit()
    return cursor.lastrowid


def ingest_prices(
    connection: sqlite3.Connection,
    provider: PriceProvider,
    company_id: int,
    symbol: str,
    currency: str,
    start_date: date,
    end_date: date,
) -> int:
    source_id = create_source(
        connection=connection,
        provider=provider.name,
        document_type="market_prices",
    )

    records = provider.get_prices(
        company_id=company_id,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )

    inserted = 0

    for record in records:
        enriched_record = PriceRecord(
            **record.model_dump(
                exclude={"currency", "source_id"}
            ),
            currency=currency,
            source_id=source_id,
        )

        insert_price_record(
            connection,
            enriched_record,
        )

        inserted += 1

    return inserted

def ingest_prices_incremental(
    connection: sqlite3.Connection,
    provider: PriceProvider,
    company_id: int,
    symbol: str,
    currency: str,
    initial_start_date: date,
    end_date: date,
) -> int:
    latest_price_date = get_latest_price_date(
        connection,
        company_id,
    )

    if latest_price_date is None:
        start_date = initial_start_date
    else:
        start_date = latest_price_date + timedelta(days=1)

    if start_date > end_date:
        return 0

    return ingest_prices(
        connection=connection,
        provider=provider,
        company_id=company_id,
        symbol=symbol,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
    )