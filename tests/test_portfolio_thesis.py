import sqlite3
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.db import connect, initialize_database
from src.models import PortfolioThesis
from src.repository import (
    get_portfolio_thesis_on_or_before,
    upsert_portfolio_thesis,
)


def create_company(
    connection,
    ticker: str = "TEST",
) -> int:
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
            "Test Company",
            ticker,
            "BME",
            "EUR",
        ),
    )
    connection.commit()
    return cursor.lastrowid


def test_portfolio_thesis_model():
    thesis = PortfolioThesis(
        company_id=1,
        effective_date="2026-01-10",
        thesis=" Durable competitive advantage. ",
        risks=" Margin compression. ",
        review_date="2026-06-30",
    )

    assert thesis.thesis == (
        "Durable competitive advantage."
    )
    assert thesis.risks == "Margin compression."
    assert thesis.effective_date == date(
        2026,
        1,
        10,
    )
    assert thesis.review_date == date(
        2026,
        6,
        30,
    )


def test_empty_thesis_is_rejected():
    with pytest.raises(ValidationError):
        PortfolioThesis(
            company_id=1,
            effective_date="2026-01-10",
            thesis="   ",
        )


def test_empty_risks_become_none():
    thesis = PortfolioThesis(
        company_id=1,
        effective_date="2026-01-10",
        thesis="Investment thesis",
        risks="   ",
    )

    assert thesis.risks is None


def test_review_date_cannot_precede_effective_date():
    with pytest.raises(
        ValidationError,
        match="review_date cannot be earlier",
    ):
        PortfolioThesis(
            company_id=1,
            effective_date="2026-01-10",
            thesis="Investment thesis",
            review_date="2026-01-09",
        )


def test_insert_and_read_thesis(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        thesis_id = upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-01-10",
                thesis="Long-term earnings growth.",
                risks="Multiple compression.",
                review_date="2026-06-30",
            ),
        )

        result = get_portfolio_thesis_on_or_before(
            connection,
            company_id=company_id,
            as_of_date=date(2026, 1, 10),
        )

    assert thesis_id > 0
    assert result is not None
    assert result.company_id == company_id
    assert result.thesis == (
        "Long-term earnings growth."
    )
    assert result.risks == "Multiple compression."
    assert result.review_date == date(
        2026,
        6,
        30,
    )


def test_future_thesis_is_not_visible(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-02-01",
                thesis="Future thesis",
            ),
        )

        result = get_portfolio_thesis_on_or_before(
            connection,
            company_id=company_id,
            as_of_date=date(2026, 1, 31),
        )

    assert result is None


def test_latest_thesis_on_or_before_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-01-01",
                thesis="Original thesis",
            ),
        )

        upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-03-01",
                thesis="Revised thesis",
            ),
        )

        january = get_portfolio_thesis_on_or_before(
            connection,
            company_id=company_id,
            as_of_date=date(2026, 2, 1),
        )

        march = get_portfolio_thesis_on_or_before(
            connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )

    assert january is not None
    assert january.thesis == "Original thesis"

    assert march is not None
    assert march.thesis == "Revised thesis"


def test_same_effective_date_updates_existing_version(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        first_id = upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-01-10",
                thesis="First text",
            ),
        )

        second_id = upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-01-10",
                thesis="Corrected text",
                risks="Corrected risks",
            ),
        )

        count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM portfolio_theses
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()["count"]

        result = get_portfolio_thesis_on_or_before(
            connection,
            company_id=company_id,
            as_of_date=date(2026, 1, 10),
        )

    assert first_id == second_id
    assert count == 1
    assert result is not None
    assert result.thesis == "Corrected text"
    assert result.risks == "Corrected risks"


def test_thesis_history_preserves_versions(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-01-01",
                thesis="Version one",
            ),
        )

        upsert_portfolio_thesis(
            connection,
            PortfolioThesis(
                company_id=company_id,
                effective_date="2026-04-01",
                thesis="Version two",
            ),
        )

        count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM portfolio_theses
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()["count"]

    assert count == 2


def test_unknown_company_is_rejected_by_foreign_key(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            upsert_portfolio_thesis(
                connection,
                PortfolioThesis(
                    company_id=999,
                    effective_date="2026-01-01",
                    thesis="Invalid company",
                ),
            )


def test_schema_version_is_0_6_0(
    tmp_path: Path,
):
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

    assert row["value"] == "0.6.0"