from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.models import EstimateRecord, FinancialRecord, PriceRecord
from src.repository import (
    insert_financial_record,
    insert_price_record,
    insert_estimate_record,
)
from src.valuation import (
    build_forward_valuation_snapshot,
    build_valuation_snapshot,
)


def create_company(connection) -> int:
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
            "TEST",
            "BME",
            "EUR",
        ),
    )
    connection.commit()
    return cursor.lastrowid


def test_build_valuation_snapshot(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-03-02",
                close=50.0,
                currency="EUR",
            ),
        )

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.50,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        snapshot = build_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 2),
        )

    assert snapshot is not None
    assert snapshot.price == 50.0
    assert snapshot.eps == 2.50
    assert snapshot.pe == pytest.approx(20.0)
    assert snapshot.earnings_yield == pytest.approx(0.05)

    assert snapshot.price_date == date(2026, 3, 2)
    assert snapshot.eps_period_end == date(2025, 12, 31)
    assert snapshot.eps_publication_date == date(2026, 2, 26)


def test_snapshot_does_not_use_unpublished_eps(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-02-20",
                close=50.0,
                currency="EUR",
            ),
        )

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.50,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        snapshot = build_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 2, 20),
        )

    assert snapshot is None


def test_snapshot_preserves_negative_eps(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-03-02",
                close=50.0,
                currency="EUR",
            ),
        )

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=-2.0,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        snapshot = build_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 2),
        )

    assert snapshot is not None
    assert snapshot.eps == -2.0
    assert snapshot.pe is None
    assert snapshot.earnings_yield is None

def test_build_forward_valuation_snapshot(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-05-15",
                close=60.0,
                currency="EUR",
            ),
        )

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.0,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-05-01",
                analyst_count=12,
            ),
        )

        snapshot = build_forward_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 5, 15),
            fiscal_period_end=date(2026, 12, 31),
        )

    assert snapshot is not None
    assert snapshot.price == 60.0
    assert snapshot.forward_eps == 3.0
    assert snapshot.forward_pe == pytest.approx(20.0)
    assert snapshot.forward_earnings_yield == pytest.approx(0.05)
    assert snapshot.estimate_date == date(2026, 5, 1)
    assert snapshot.analyst_count == 12


def test_forward_snapshot_does_not_use_future_revision(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-05-15",
                close=60.0,
                currency="EUR",
            ),
        )

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.0,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-05-01",
            ),
        )

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=4.0,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-06-01",
            ),
        )

        snapshot = build_forward_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 5, 15),
            fiscal_period_end=date(2026, 12, 31),
        )

    assert snapshot is not None
    assert snapshot.forward_eps == 3.0
    assert snapshot.estimate_date == date(2026, 5, 1)
    assert snapshot.forward_pe == pytest.approx(20.0)


def test_forward_snapshot_returns_none_without_known_estimate(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-05-15",
                close=60.0,
                currency="EUR",
            ),
        )

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.0,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-06-01",
            ),
        )

        snapshot = build_forward_valuation_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 5, 15),
            fiscal_period_end=date(2026, 12, 31),
        )

    assert snapshot is None