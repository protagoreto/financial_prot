from datetime import date, datetime, timedelta, timezone
import sqlite3

from src.models import EstimateRecord, FinancialRecord, PriceRecord
from src.providers.base import PriceProvider
from src.repository import (
    insert_estimate_record,
    insert_financial_record,
    insert_price_record,
)
def get_or_create_company(
    connection: sqlite3.Connection,
    name: str,
    ticker: str,
    exchange: str,
    currency: str,
    fundamental_profile: str = "operating",
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
            currency,
            fundamental_profile
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            ticker,
            exchange,
            currency,
            fundamental_profile,
        ),
    )

    connection.commit()
    return cursor.lastrowid


def create_source(
    connection: sqlite3.Connection,
    provider: str,
    document_type: str,
    url: str | None = None,
    publication_date: date | None = None,
    confidence: str = "secondary",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO sources (
            provider,
            url,
            retrieved_at,
            publication_date,
            document_type,
            confidence
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            provider,
            url,
            datetime.now(timezone.utc).isoformat(),
            (
                publication_date.isoformat()
                if publication_date
                else None
            ),
            document_type,
            confidence,
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
    row = connection.execute(
        """
        SELECT
            MIN(price_date) AS first_price_date,
            MAX(price_date) AS latest_price_date
        FROM prices
        WHERE company_id = ?
        """,
        (company_id,),
    ).fetchone()

    first_price_date = (
        date.fromisoformat(row["first_price_date"])
        if row["first_price_date"]
        else None
    )

    latest_price_date = (
        date.fromisoformat(row["latest_price_date"])
        if row["latest_price_date"]
        else None
    )

    total_processed = 0

    # Backfill missing historical data.
    if (
        first_price_date is not None
        and (first_price_date - initial_start_date).days > 7
    ):
        historical_end_date = first_price_date - timedelta(days=1)

        total_processed += ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol=symbol,
            currency=currency,
            start_date=initial_start_date,
            end_date=historical_end_date,
        )

    # No existing prices: perform the initial load.
    if latest_price_date is None:
        total_processed += ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol=symbol,
            currency=currency,
            start_date=initial_start_date,
            end_date=end_date,
        )

        return total_processed

    # Forward incremental update.
    forward_start_date = latest_price_date + timedelta(days=1)

    if forward_start_date <= end_date:
        total_processed += ingest_prices(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol=symbol,
            currency=currency,
            start_date=forward_start_date,
            end_date=end_date,
        )

    return total_processed

def ingest_financials(
    connection: sqlite3.Connection,
    provider,
    company_id: int,
    symbol: str,
    currency: str,
) -> int:
    source_id = create_source(
        connection=connection,
        provider=provider.name,
        document_type="annual_financials",
    )

    records = provider.get_annual_financials(
        company_id=company_id,
        symbol=symbol,
    )

    processed = 0

    for record in records:
        enriched_record = FinancialRecord(
            **record.model_dump(
                exclude={
                    "currency",
                    "source_id",
                }
            ),
            currency=currency,
            source_id=source_id,
        )

        insert_financial_record(
            connection,
            enriched_record,
        )

        processed += 1

    return processed

def ingest_forward_eps_estimate(
    connection: sqlite3.Connection,
    provider,
    company_id: int,
    symbol: str,
    estimate_date: date | None = None,
) -> int:
    record = provider.get_forward_eps_estimate(
        company_id=company_id,
        symbol=symbol,
        estimate_date=estimate_date,
    )

    existing = connection.execute(
        """
        SELECT estimate_id
        FROM estimates
        WHERE company_id = ?
        AND metric = ?
        AND fiscal_period_end = ?
        AND estimate_date = ?
        """,
        (
            record.company_id,
            record.metric.value,
            record.fiscal_period_end.isoformat(),
            record.estimate_date.isoformat(),
        ),
    ).fetchone()

    if existing is not None:
        return existing["estimate_id"]

    source_id = create_source(
        connection=connection,
        provider=provider.name,
        document_type="forward_estimate",
        publication_date=record.estimate_date,
        confidence="secondary",
    )

    enriched_record = EstimateRecord(
        **record.model_dump(
            exclude={"source_id"}
        ),
        source_id=source_id,
    )

    return insert_estimate_record(
        connection,
        enriched_record,
    )
