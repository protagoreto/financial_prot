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
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """
    Open a SQLite connection and ensure the parent directory exists.
    """

    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database(db_path: Path) -> None:
    """
    Create the database schema if it does not already exist.
    """

    with connect(db_path) as connection:

        connection.executescript(SCHEMA)

        connection.execute(
            """
            INSERT OR IGNORE INTO schema_meta(key, value)
            VALUES (?, ?)
            """,
            ("schema_version", "0.1.0"),
        )

        connection.commit()
