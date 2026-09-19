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

    assert "schema_meta" in tables
    assert "companies" in tables
    assert "sources" in tables
    assert "analysis_runs" in tables


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

    assert row["value"] == "0.1.0"
