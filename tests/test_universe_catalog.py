import sqlite3
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.universe_catalog import (
    load_universe_catalog,
    sync_universe_catalog,
)


def _write_catalog(
    path: Path,
    rows: str,
) -> Path:
    path.write_text(
        (
            "name,ticker,symbol,exchange,currency,"
            "fundamental_profile\n"
            + rows
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_load_universe_catalog(
    tmp_path: Path,
) -> None:
    path = _write_catalog(
        tmp_path / "universe.csv",
        (
            "Example,abc,ABC.MC,bme,eur,operating\n"
            "Bank,bank,BANK.MC,bme,eur,financial\n"
        ),
    )

    companies = load_universe_catalog(path)

    assert len(companies) == 2

    assert companies[0].ticker == "ABC"
    assert companies[0].exchange == "BME"
    assert companies[0].currency == "EUR"
    assert companies[0].fundamental_profile == "operating"

    assert companies[1].fundamental_profile == "financial"


def test_catalog_rejects_duplicate_identity(
    tmp_path: Path,
) -> None:
    path = _write_catalog(
        tmp_path / "universe.csv",
        (
            "One,ABC,ABC.MC,BME,EUR,operating\n"
            "Two,abc,ABC2.MC,bme,EUR,operating\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate company identity",
    ):
        load_universe_catalog(path)


def test_catalog_rejects_duplicate_symbol(
    tmp_path: Path,
) -> None:
    path = _write_catalog(
        tmp_path / "universe.csv",
        (
            "One,ABC,ABC.MC,BME,EUR,operating\n"
            "Two,DEF,abc.mc,BME,EUR,operating\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate symbol",
    ):
        load_universe_catalog(path)


def test_catalog_rejects_invalid_profile(
    tmp_path: Path,
) -> None:
    path = _write_catalog(
        tmp_path / "universe.csv",
        "One,ABC,ABC.MC,BME,EUR,unknown\n",
    )

    with pytest.raises(
        ValueError,
        match="invalid fundamental_profile",
    ):
        load_universe_catalog(path)


def test_sync_is_idempotent(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    catalog = _write_catalog(
        tmp_path / "universe.csv",
        (
            "One,ABC,ABC.MC,BME,EUR,operating\n"
            "Bank,XYZ,XYZ.MC,BME,EUR,financial\n"
        ),
    )

    companies = load_universe_catalog(catalog)

    with connect(db_path) as connection:
        first = sync_universe_catalog(
            connection,
            companies,
        )
        second = sync_universe_catalog(
            connection,
            companies,
        )

        count = connection.execute(
            "SELECT COUNT(*) AS count FROM companies"
        ).fetchone()["count"]

    assert first.created == 2
    assert first.existing == 0

    assert second.created == 0
    assert second.existing == 2

    assert count == 2


def test_sync_matches_identity_case_insensitively(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        connection.execute(
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
                "Existing",
                "abc",
                "bme",
                "EUR",
                "operating",
            ),
        )
        connection.commit()

    catalog = _write_catalog(
        tmp_path / "universe.csv",
        "Existing,ABC,ABC.MC,BME,EUR,operating\n",
    )

    companies = load_universe_catalog(catalog)

    with connect(db_path) as connection:
        result = sync_universe_catalog(
            connection,
            companies,
        )

        count = connection.execute(
            "SELECT COUNT(*) AS count FROM companies"
        ).fetchone()["count"]

    assert result.created == 0
    assert result.existing == 1
    assert count == 1


def test_sync_universe_catalog_persists_symbol(tmp_path):
    from src.db import connect, initialize_database
    from src.universe import CompanyConfig

    db_path = tmp_path / "symbol.sqlite"
    initialize_database(db_path)

    companies = (
        CompanyConfig(
            name="Microsoft Corporation",
            ticker="MSFT",
            symbol="MSFT",
            exchange="NMS",
            currency="USD",
            fundamental_profile="operating",
        ),
    )

    with connect(db_path) as connection:
        result = sync_universe_catalog(
            connection,
            companies,
        )

        row = connection.execute(
            """
            SELECT symbol
            FROM companies
            WHERE ticker = 'MSFT'
            AND exchange = 'NMS'
            """
        ).fetchone()

    assert result.created == 1
    assert row["symbol"] == "MSFT"


def test_sync_universe_catalog_backfills_symbol(tmp_path):
    from src.db import connect, initialize_database
    from src.universe import CompanyConfig

    db_path = tmp_path / "backfill_symbol.sqlite"
    initialize_database(db_path)

    companies = (
        CompanyConfig(
            name="Microsoft Corporation",
            ticker="MSFT",
            symbol="MSFT",
            exchange="NMS",
            currency="USD",
            fundamental_profile="operating",
        ),
    )

    with connect(db_path) as connection:
        connection.execute(
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
                "Microsoft Corporation",
                "MSFT",
                "NMS",
                "USD",
            ),
        )
        connection.commit()

        result = sync_universe_catalog(
            connection,
            companies,
        )

        row = connection.execute(
            """
            SELECT symbol
            FROM companies
            WHERE ticker = 'MSFT'
            AND exchange = 'NMS'
            """
        ).fetchone()

    assert result.existing == 1
    assert row["symbol"] == "MSFT"


def test_sync_universe_catalog_rejects_symbol_conflict(
    tmp_path,
):
    import pytest

    from src.db import connect, initialize_database
    from src.universe import CompanyConfig

    db_path = tmp_path / "symbol_conflict.sqlite"
    initialize_database(db_path)

    companies = (
        CompanyConfig(
            name="Microsoft Corporation",
            ticker="MSFT",
            symbol="MSFT",
            exchange="NMS",
            currency="USD",
            fundamental_profile="operating",
        ),
    )

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO companies (
                name,
                ticker,
                symbol,
                exchange,
                currency
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Microsoft Corporation",
                "MSFT",
                "WRONG",
                "NMS",
                "USD",
            ),
        )
        connection.commit()

        with pytest.raises(
            ValueError,
            match="different symbol",
        ):
            sync_universe_catalog(
                connection,
                companies,
            )
