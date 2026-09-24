from pathlib import Path

from scripts.universe import main
from src.db import connect, initialize_database


def _catalog(path: Path) -> Path:
    path.write_text(
        (
            "name,ticker,symbol,exchange,currency,"
            "fundamental_profile\n"
            "Example,ABC,ABC.MC,BME,EUR,operating\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_cli_validation_only(
    tmp_path: Path,
    capsys,
) -> None:
    catalog = _catalog(
        tmp_path / "universe.csv"
    )

    exit_code = main([str(catalog)])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "companies: 1" in output
    assert "mode: validation_only" in output


def test_cli_sync(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    catalog = _catalog(
        tmp_path / "universe.csv"
    )

    exit_code = main(
        [
            str(catalog),
            "--db-path",
            str(db_path),
            "--sync",
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "mode: synchronized" in output
    assert "created: 1" in output

    with connect(db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM companies"
        ).fetchone()["count"]

    assert count == 1
