from datetime import date
import sqlite3

import pytest

from src.coverage import (
    CompanyCoverage,
    build_company_coverage,
)
from src.db import initialize_database
from src.ingestion import get_or_create_company
from src.investment import AnalysisAvailability


def test_company_coverage_availability_complete():
    coverage = CompanyCoverage(
        company_id=1,
        as_of_date=date(2026, 9, 23),
        price_available=True,
        fundamental_snapshot_available=True,
        fundamental_growth_available=True,
        forward_eps_period=date(2027, 1, 31),
        estimate_count=1,
        dividend_count=0,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )

    assert coverage.fundamentals_available
    assert coverage.valuation_inputs_available
    assert coverage.availability == AnalysisAvailability.COMPLETE


def test_company_coverage_availability_fundamentals_only():
    coverage = CompanyCoverage(
        company_id=1,
        as_of_date=date(2026, 9, 23),
        price_available=True,
        fundamental_snapshot_available=True,
        fundamental_growth_available=True,
        forward_eps_period=None,
        estimate_count=0,
        dividend_count=0,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )

    assert coverage.fundamentals_available
    assert not coverage.valuation_inputs_available
    assert (
        coverage.availability
        == AnalysisAvailability.FUNDAMENTALS_ONLY
    )


def test_company_coverage_availability_valuation_only():
    coverage = CompanyCoverage(
        company_id=1,
        as_of_date=date(2026, 9, 23),
        price_available=True,
        fundamental_snapshot_available=False,
        fundamental_growth_available=False,
        forward_eps_period=date(2027, 1, 31),
        estimate_count=1,
        dividend_count=0,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )

    assert not coverage.fundamentals_available
    assert coverage.valuation_inputs_available
    assert (
        coverage.availability
        == AnalysisAvailability.VALUATION_ONLY
    )


def test_company_coverage_availability_insufficient():
    coverage = CompanyCoverage(
        company_id=1,
        as_of_date=date(2026, 9, 23),
        price_available=True,
        fundamental_snapshot_available=False,
        fundamental_growth_available=False,
        forward_eps_period=None,
        estimate_count=0,
        dividend_count=0,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )

    assert not coverage.fundamentals_available
    assert not coverage.valuation_inputs_available
    assert (
        coverage.availability
        == AnalysisAvailability.INSUFFICIENT
    )


def test_build_company_coverage_for_empty_company(tmp_path):
    db_path = tmp_path / "coverage.sqlite"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        company_id = get_or_create_company(
            connection=connection,
            name="Example Company",
            ticker="EX",
            exchange="BME",
            currency="EUR",
        )

        coverage = build_company_coverage(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 9, 23),
        )

        assert coverage.company_id == company_id
        assert not coverage.price_available
        assert not coverage.fundamental_snapshot_available
        assert not coverage.fundamental_growth_available
        assert coverage.forward_eps_period is None
        assert coverage.estimate_count == 0
        assert coverage.dividend_count == 0
        assert coverage.missing_snapshot_metrics
        assert coverage.missing_growth_metrics
        assert (
            coverage.availability
            == AnalysisAvailability.INSUFFICIENT
        )
    finally:
        connection.close()


def test_build_company_coverage_rejects_invalid_company_id(
    tmp_path,
):
    db_path = tmp_path / "coverage.sqlite"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        with pytest.raises(
            ValueError,
            match="company_id must be greater than zero",
        ):
            build_company_coverage(
                connection=connection,
                company_id=0,
                as_of_date=date(2026, 9, 23),
            )
    finally:
        connection.close()


def test_build_company_coverage_rejects_unknown_company(
    tmp_path,
):
    db_path = tmp_path / "coverage.sqlite"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        with pytest.raises(
            ValueError,
            match="Coverage company does not exist",
        ):
            build_company_coverage(
                connection=connection,
                company_id=999,
                as_of_date=date(2026, 9, 23),
            )
    finally:
        connection.close()

def test_metric_presence_does_not_imply_growth_availability(
    tmp_path,
):
    db_path = tmp_path / "coverage.sqlite"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        company_id = get_or_create_company(
            connection=connection,
            name="Example Company",
            ticker="EX",
            exchange="BME",
            currency="EUR",
        )

        metrics = (
            "revenue",
            "ebitda",
            "ebit",
            "net_income",
            "eps",
            "free_cash_flow",
            "shares_outstanding",
            "equity",
        )

        source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                document_type,
                retrieved_at,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "test",
                "annual_results",
                "2026-03-01T00:00:00",
                "primary",
            ),
        ).lastrowid

        for metric in metrics:
            connection.execute(
                """
                INSERT INTO financials (
                    company_id,
                    statement_type,
                    metric,
                    value,
                    currency,
                    period_end,
                    period_type,
                    publication_date,
                    source_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    (
                        "per_share"
                        if metric == "eps"
                        else "income_statement"
                    ),
                    metric,
                    100.0,
                    "EUR",
                    "2025-12-31",
                    "annual",
                    "2026-03-01",
                    source_id,
                ),
            )

        connection.commit()

        coverage = build_company_coverage(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 9, 23),
        )

        assert coverage.missing_growth_metrics == ()
        assert not coverage.fundamental_growth_available
        assert not coverage.fundamentals_available
    finally:
        connection.close()
