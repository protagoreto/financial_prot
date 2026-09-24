import sqlite3
from datetime import date


from src.models import (
    AnalysisRunRecord,
    CompanyRecord,
    DividendRecord,
    EstimateRecord,
    FinancialRecord,
    PortfolioThesis,
    PortfolioTransaction,
    PriceRecord,
)

from src.metrics import FinancialMetric, PeriodType



def insert_dividend_record(
    connection: sqlite3.Connection,
    record: DividendRecord,
) -> int:
    existing = connection.execute(
        """
        SELECT dividend_id
        FROM dividends
        WHERE company_id = ?
        AND ex_date = ?
        AND amount = ?
        """,
        (
            record.company_id,
            record.ex_date.isoformat(),
            record.amount,
        ),
    ).fetchone()

    if existing is not None:
        return existing["dividend_id"]

    cursor = connection.execute(
        """
        INSERT INTO dividends (
            company_id,
            ex_date,
            payment_date,
            amount,
            currency,
            dividend_type,
            source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.company_id,
            record.ex_date.isoformat(),
            (
                record.payment_date.isoformat()
                if record.payment_date is not None
                else None
            ),
            record.amount,
            record.currency,
            record.dividend_type,
            record.source_id,
        ),
    )

    connection.commit()
    return cursor.lastrowid

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
            f.company_id,
            f.statement_type,
            f.metric,
            f.value,
            f.currency,
            f.period_start,
            f.period_end,
            f.period_type,
            COALESCE(
                f.publication_date,
                (
                    SELECT pd.publication_date
                    FROM publication_dates AS pd
                    WHERE pd.company_id = f.company_id
                    AND pd.period_end = f.period_end
                    AND pd.period_type = f.period_type
                    ORDER BY pd.publication_date DESC
                    LIMIT 1
                )
            ) AS effective_publication_date,
            f.source_id
        FROM financials AS f
        WHERE f.company_id = ?
        AND f.metric = ?
        AND f.period_type = ?
        AND COALESCE(
            f.publication_date,
            (
                SELECT pd.publication_date
                FROM publication_dates AS pd
                WHERE pd.company_id = f.company_id
                AND pd.period_end = f.period_end
                AND pd.period_type = f.period_type
                ORDER BY pd.publication_date DESC
                LIMIT 1
            )
        ) <= ?
        ORDER BY
            effective_publication_date DESC,
            f.period_end DESC
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
        publication_date=row[
            "effective_publication_date"
        ],
        source_id=row["source_id"],
    )

def get_financial_for_period_on_or_before(
    connection: sqlite3.Connection,
    company_id: int,
    metric: FinancialMetric,
    period_end: date,
    as_of_date: date,
    period_type: PeriodType,
) -> FinancialRecord | None:
    row = connection.execute(
        """
        SELECT
            f.company_id,
            f.statement_type,
            f.metric,
            f.value,
            f.currency,
            f.period_start,
            f.period_end,
            f.period_type,
            COALESCE(
                f.publication_date,
                (
                    SELECT pd.publication_date
                    FROM publication_dates AS pd
                    WHERE pd.company_id = f.company_id
                    AND pd.period_end = f.period_end
                    AND pd.period_type = f.period_type
                    ORDER BY pd.publication_date DESC
                    LIMIT 1
                )
            ) AS effective_publication_date,
            f.source_id
        FROM financials AS f
        WHERE f.company_id = ?
        AND f.metric = ?
        AND f.period_end = ?
        AND f.period_type = ?
        AND COALESCE(
            f.publication_date,
            (
                SELECT pd.publication_date
                FROM publication_dates AS pd
                WHERE pd.company_id = f.company_id
                AND pd.period_end = f.period_end
                AND pd.period_type = f.period_type
                ORDER BY pd.publication_date DESC
                LIMIT 1
            )
        ) <= ?
        ORDER BY effective_publication_date DESC
        LIMIT 1
        """,
        (
            company_id,
            metric.value,
            period_end.isoformat(),
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
        publication_date=row[
            "effective_publication_date"
        ],
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


def get_next_estimate_period_on_or_after(
    connection: sqlite3.Connection,
    company_id: int,
    metric: FinancialMetric,
    as_of_date: date,
) -> date | None:
    if company_id <= 0:
        raise ValueError(
            "company_id must be positive"
        )

    row = connection.execute(
        """
        SELECT fiscal_period_end
        FROM estimates
        WHERE company_id = ?
        AND metric = ?
        AND estimate_date <= ?
        AND fiscal_period_end >= ?
        ORDER BY fiscal_period_end ASC
        LIMIT 1
        """,
        (
            company_id,
            metric.value,
            as_of_date.isoformat(),
            as_of_date.isoformat(),
        ),
    ).fetchone()

    if row is None:
        return None

    return date.fromisoformat(
        row["fiscal_period_end"]
    )


def insert_publication_date(
    connection: sqlite3.Connection,
    company_id: int,
    period_end: date,
    period_type: PeriodType,
    publication_date: date,
    source_id: int,
) -> int:
    if publication_date < period_end:
        raise ValueError(
            "Publication date cannot be earlier "
            "than period end."
        )

    existing = connection.execute(
        """
        SELECT publication_date_id
        FROM publication_dates
        WHERE company_id = ?
        AND period_end = ?
        AND period_type = ?
        AND publication_date = ?
        """,
        (
            company_id,
            period_end.isoformat(),
            period_type.value,
            publication_date.isoformat(),
        ),
    ).fetchone()

    if existing is not None:
        return existing["publication_date_id"]

    cursor = connection.execute(
        """
        INSERT INTO publication_dates (
            company_id,
            period_end,
            period_type,
            publication_date,
            source_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            company_id,
            period_end.isoformat(),
            period_type.value,
            publication_date.isoformat(),
            source_id,
        ),
    )

    connection.commit()

    return cursor.lastrowid
def get_verified_publication_date(
    connection: sqlite3.Connection,
    company_id: int,
    period_end: date,
    period_type: PeriodType,
) -> date | None:
    row = connection.execute(
        """
        SELECT publication_date
        FROM publication_dates
        WHERE company_id = ?
        AND period_end = ?
        AND period_type = ?
        ORDER BY publication_date DESC
        LIMIT 1
        """,
        (
            company_id,
            period_end.isoformat(),
            period_type.value,
        ),
    ).fetchone()

    if row is None:
        return None

    return date.fromisoformat(
        row["publication_date"]
    )

def insert_portfolio_transaction(
    connection: sqlite3.Connection,
    transaction: PortfolioTransaction,
) -> int:
    connection.execute(
        """
        INSERT INTO portfolio_transactions (
            external_id,
            transaction_date,
            transaction_type,
            company_id,
            quantity,
            price,
            amount,
            fee,
            tax,
            currency,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(external_id)
        DO NOTHING
        """,
        (
            transaction.external_id,
            transaction.transaction_date.isoformat(),
            transaction.transaction_type.value,
            transaction.company_id,
            transaction.quantity,
            transaction.price,
            transaction.amount,
            transaction.fee,
            transaction.tax,
            transaction.currency.upper(),
            transaction.note,
        ),
    )

    row = connection.execute(
        """
        SELECT transaction_id
        FROM portfolio_transactions
        WHERE external_id = ?
        """,
        (transaction.external_id,),
    ).fetchone()

    connection.commit()

    return row["transaction_id"]


def get_portfolio_transactions(
    connection: sqlite3.Connection,
    as_of_date: date | None = None,
) -> tuple[PortfolioTransaction, ...]:
    parameters: tuple[str, ...] = ()

    where_clause = ""

    if as_of_date is not None:
        where_clause = (
            "WHERE transaction_date <= ?"
        )
        parameters = (
            as_of_date.isoformat(),
        )

    rows = connection.execute(
        f"""
        SELECT
            external_id,
            transaction_date,
            transaction_type,
            company_id,
            quantity,
            price,
            amount,
            fee,
            tax,
            currency,
            note
        FROM portfolio_transactions
        {where_clause}
        ORDER BY
            transaction_date ASC,
            transaction_id ASC
        """,
        parameters,
    ).fetchall()

    return tuple(
        PortfolioTransaction(
            external_id=row["external_id"],
            transaction_date=row[
                "transaction_date"
            ],
            transaction_type=row[
                "transaction_type"
            ],
            company_id=row["company_id"],
            quantity=row["quantity"],
            price=row["price"],
            amount=row["amount"],
            fee=row["fee"],
            tax=row["tax"],
            currency=row["currency"],
            note=row["note"],
        )
        for row in rows
    )


def get_company_id_by_ticker_exchange(
    connection: sqlite3.Connection,
    ticker: str,
    exchange: str,
) -> int | None:
    normalized_ticker = ticker.strip().upper()
    normalized_exchange = exchange.strip().upper()

    if not normalized_ticker:
        raise ValueError("ticker cannot be empty")

    if not normalized_exchange:
        raise ValueError("exchange cannot be empty")

    row = connection.execute(
        """
        SELECT company_id
        FROM companies
        WHERE UPPER(ticker) = ?
        AND UPPER(exchange) = ?
        """,
        (
            normalized_ticker,
            normalized_exchange,
        ),
    ).fetchone()

    if row is None:
        return None

    return row["company_id"]


def get_company_by_id(
    connection: sqlite3.Connection,
    company_id: int,
) -> CompanyRecord | None:
    if company_id <= 0:
        raise ValueError("company_id must be positive")

    row = connection.execute(
        """
        SELECT
            company_id,
            name,
            ticker,
            isin,
            country,
            sector,
            industry,
            fundamental_profile,
            currency,
            exchange,
            status
        FROM companies
        WHERE company_id = ?
        """,
        (company_id,),
    ).fetchone()

    if row is None:
        return None

    return CompanyRecord(
        company_id=row["company_id"],
        name=row["name"],
        ticker=row["ticker"],
        isin=row["isin"],
        country=row["country"],
        sector=row["sector"],
        industry=row["industry"],
        fundamental_profile=row[
            "fundamental_profile"
        ],
        currency=row["currency"],
        exchange=row["exchange"],
        status=row["status"],
    )


def upsert_portfolio_thesis(
    connection: sqlite3.Connection,
    thesis: PortfolioThesis,
) -> int:
    connection.execute(
        """
        INSERT INTO portfolio_theses (
            company_id,
            effective_date,
            thesis,
            risks,
            review_date
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(company_id, effective_date)
        DO UPDATE SET
            thesis = excluded.thesis,
            risks = excluded.risks,
            review_date = excluded.review_date
        """,
        (
            thesis.company_id,
            thesis.effective_date.isoformat(),
            thesis.thesis,
            thesis.risks,
            (
                thesis.review_date.isoformat()
                if thesis.review_date
                else None
            ),
        ),
    )

    row = connection.execute(
        """
        SELECT thesis_id
        FROM portfolio_theses
        WHERE company_id = ?
        AND effective_date = ?
        """,
        (
            thesis.company_id,
            thesis.effective_date.isoformat(),
        ),
    ).fetchone()

    connection.commit()

    return row["thesis_id"]


def get_portfolio_thesis_on_or_before(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> PortfolioThesis | None:
    row = connection.execute(
        """
        SELECT
            company_id,
            effective_date,
            thesis,
            risks,
            review_date
        FROM portfolio_theses
        WHERE company_id = ?
        AND effective_date <= ?
        ORDER BY effective_date DESC
        LIMIT 1
        """,
        (
            company_id,
            as_of_date.isoformat(),
        ),
    ).fetchone()

    if row is None:
        return None

    return PortfolioThesis(
        company_id=row["company_id"],
        effective_date=row["effective_date"],
        thesis=row["thesis"],
        risks=row["risks"],
        review_date=row["review_date"],
    )


def insert_analysis_run(
    connection: sqlite3.Connection,
    record: AnalysisRunRecord,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO analysis_runs (
            model_version,
            data_version,
            company_id,
            status,
            execution_time,
            error
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            record.model_version,
            record.data_version,
            record.company_id,
            record.status.value,
            record.execution_time,
            record.error,
        ),
    )

    connection.commit()
    return cursor.lastrowid


def get_price_on_or_after(
    connection: sqlite3.Connection,
    company_id: int,
    target_date: date,
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
        AND price_date >= ?
        ORDER BY price_date ASC
        LIMIT 1
        """,
        (
            company_id,
            target_date.isoformat(),
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
