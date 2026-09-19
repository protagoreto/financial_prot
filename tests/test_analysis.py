from datetime import date
from pathlib import Path

import pytest

from src.analysis import build_valuation_analysis
from src.db import connect, initialize_database
from src.models import EstimateRecord, PriceRecord
from src.repository import (
    insert_estimate_record,
    insert_price_record,
)
from src.scenarios import ValuationScenario


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


def test_build_complete_valuation_analysis(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    scenarios = (
        ValuationScenario(
            name="Conservative",
            eps_growth=0.03,
            dividend_yield=0.02,
            terminal_pe=12.0,
        ),
        ValuationScenario(
            name="Base",
            eps_growth=0.08,
            dividend_yield=0.02,
            terminal_pe=15.0,
        ),
        ValuationScenario(
            name="Optimistic",
            eps_growth=0.12,
            dividend_yield=0.02,
            terminal_pe=18.0,
        ),
    )

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

        analysis = build_valuation_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 5, 15),
            fiscal_period_end=date(2026, 12, 31),
            scenarios=scenarios,
            target_return=0.10,
            years=5,
        )

    assert analysis is not None

    assert analysis.snapshot.price == 60.0
    assert analysis.snapshot.forward_eps == 3.0
    assert analysis.snapshot.forward_pe == pytest.approx(20.0)

    assert analysis.target_return == 0.10
    assert analysis.years == 5

    assert len(analysis.scenarios) == 3

    assert [
        result.name
        for result in analysis.scenarios
    ] == [
        "Conservative",
        "Base",
        "Optimistic",
    ]


def test_analysis_returns_none_without_estimate(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    scenarios = (
        ValuationScenario(
            name="Base",
            eps_growth=0.08,
            dividend_yield=0.02,
            terminal_pe=15.0,
        ),
    )

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

        analysis = build_valuation_analysis(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 5, 15),
            fiscal_period_end=date(2026, 12, 31),
            scenarios=scenarios,
        )

    assert analysis is None