import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;


CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS companies (
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker, exchange)
);


CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    url TEXT,
    retrieved_at TEXT NOT NULL,
    publication_date TEXT,
    document_type TEXT,
    confidence TEXT
);


CREATE TABLE IF NOT EXISTS prices (
    price_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    adjusted_close REAL,
    volume REAL,
    currency TEXT,
    source_id INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY(source_id)
        REFERENCES sources(source_id),

    UNIQUE(company_id, price_date)
);


CREATE TABLE IF NOT EXISTS financials (
    financial_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,

    statement_type TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT,

    period_start TEXT,
    period_end TEXT NOT NULL,
    period_type TEXT NOT NULL,

    publication_date TEXT,
    source_id INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY(source_id)
        REFERENCES sources(source_id),

    UNIQUE(
        company_id,
        statement_type,
        metric,
        period_end,
        period_type,
        source_id
    )
);


CREATE TABLE IF NOT EXISTS publication_dates (
    publication_date_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    period_end TEXT NOT NULL,
    period_type TEXT NOT NULL,
    publication_date TEXT NOT NULL,
    source_id INTEGER NOT NULL,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY(source_id)
        REFERENCES sources(source_id),

    UNIQUE(
        company_id,
        period_end,
        period_type,
        source_id
    )
);


CREATE TABLE IF NOT EXISTS estimates (
    estimate_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,

    metric TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT,

    fiscal_period_end TEXT NOT NULL,
    estimate_date TEXT NOT NULL,

    analyst_count INTEGER,
    source_id INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY(source_id)
        REFERENCES sources(source_id),

    UNIQUE(
        company_id,
        metric,
        fiscal_period_end,
        estimate_date,
        source_id
    )
);


CREATE TABLE IF NOT EXISTS dividends (
    dividend_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,

    ex_date TEXT NOT NULL,
    payment_date TEXT,
    amount REAL NOT NULL,
    currency TEXT,

    dividend_type TEXT,
    source_id INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY(source_id)
        REFERENCES sources(source_id),

    UNIQUE(
        company_id,
        ex_date,
        amount
    )
);


CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT NOT NULL,
    data_version TEXT NOT NULL,
    company_id INTEGER,
    status TEXT NOT NULL,
    execution_time REAL,
    error TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id)
);


CREATE TABLE IF NOT EXISTS portfolio_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,

    external_id TEXT NOT NULL UNIQUE,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL,

    company_id INTEGER,

    quantity REAL,
    price REAL,
    amount REAL,

    fee REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,

    currency TEXT NOT NULL,
    note TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(company_id)
        REFERENCES companies(company_id),

    CHECK (
        transaction_type IN (
            'buy',
            'sell',
            'dividend',
            'fee',
            'tax',
            'cash'
        )
    ),

    CHECK (
        quantity IS NULL
        OR quantity > 0
    ),

    CHECK (
        price IS NULL
        OR price > 0
    ),

    CHECK (fee >= 0),
    CHECK (tax >= 0),
    CHECK (length(currency) = 3)
);


CREATE INDEX IF NOT EXISTS idx_prices_company_date
ON prices(company_id, price_date);


CREATE INDEX IF NOT EXISTS idx_financials_company_period
ON financials(company_id, period_end);


CREATE INDEX IF NOT EXISTS idx_estimates_company_date
ON estimates(company_id, estimate_date);


CREATE INDEX IF NOT EXISTS idx_dividends_company_date
ON dividends(company_id, ex_date);


CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_date
ON portfolio_transactions(transaction_date);


CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_company_date
ON portfolio_transactions(
    company_id,
    transaction_date
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """
    Open a SQLite connection and ensure the parent directory exists.
    """

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def initialize_database(db_path: Path) -> None:
    """
    Create the database schema if it does not already exist.
    """

    with connect(db_path) as connection:
        connection.executescript(SCHEMA)

        connection.execute(
            """
            INSERT OR REPLACE INTO schema_meta(
                key,
                value
            )
            VALUES (?, ?)
            """,
            (
                "schema_version",
                "0.4.0",
            ),
        )

        connection.commit()