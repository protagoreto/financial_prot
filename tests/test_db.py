from pathlib import Path
from src.db import connect, initialize_database

def test_database_initializes(tmp_path: Path):
    db = tmp_path / "test.sqlite"
    initialize_database(db)
    with connect(db) as conn:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    assert {"schema_meta", "companies", "sources", "analysis_runs"} <= tables

def test_schema_version(tmp_path: Path):
    db = tmp_path / "test.sqlite"
    initialize_database(db)
    with connect(db) as conn:
        version = conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()["value"]
    assert version == "0.1.0"
