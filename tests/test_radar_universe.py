from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.ingestion import get_or_create_company
from src.metrics import FinancialMetric
from src.models import EstimateRecord
from src.radar_universe import (
    RadarUniverseIssue,
    resolve_radar_universe,
)
from src.repository import insert_estimate_record
from src.universe import CompanyConfig


AS_OF_DATE = date(2026, 9, 22)


def _company(
    ticker: str = "TEST",
    exchange: str = "BME",
) -> CompanyConfig:
    return CompanyConfig(
        name=f"{ticker} Company",
        ticker=ticker,
        symbol=f"{ticker}.MC",
        exchange=exchange,
        currency="EUR",
    )


def _insert_company(
    connection,
    company: CompanyConfig,
) -> int:
    return get_or_create_company(
        connection=connection,
        name=company.name,
        ticker=company.ticker,
        exchange=company.exchange,
        currency=company.currency,
    )


def _insert_eps_estimate(
    connection,
    company_id: int,
    fiscal_period_end: date,
    estimate_date: date,
) -> None:
    insert_estimate_record(
        connection,
        EstimateRecord(
            company_id=company_id,
            metric=FinancialMetric.EPS,
            value=2.0,
            fiscal_period_end=fiscal_period_end,
            estimate_date=estimate_date,
        ),
    )


def test_resolve_radar_universe_builds_inputs(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    company = _company()

    with connect(db_path) as connection:
        company_id = _insert_company(
            connection,
            company,
        )
        _insert_eps_estimate(
            connection=connection,
            company_id=company_id,
            fiscal_period_end=date(2026, 12, 31),
            estimate_date=date(2026, 9, 1),
        )

        result = resolve_radar_universe(
            connection=connection,
            universe=(company,),
            as_of_date=AS_OF_DATE,
        )

    assert len(result.inputs) == 1
    assert result.inputs[0].company_id == company_id
    assert (
        result.inputs[0].fiscal_period_end
        == date(2026, 12, 31)
    )
    assert result.unresolved == ()


def test_resolve_radar_universe_preserves_order(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    first = _company("AAA")
    second = _company("BBB")

    with connect(db_path) as connection:
        first_id = _insert_company(connection, first)
        second_id = _insert_company(connection, second)

        _insert_eps_estimate(
            connection,
            first_id,
            date(2026, 12, 31),
            date(2026, 9, 1),
        )
        _insert_eps_estimate(
            connection,
            second_id,
            date(2027, 3, 31),
            date(2026, 9, 1),
        )

        result = resolve_radar_universe(
            connection=connection,
            universe=(second, first),
            as_of_date=AS_OF_DATE,
        )

    assert [
        item.company_id
        for item in result.inputs
    ] == [
        second_id,
        first_id,
    ]


def test_resolve_radar_universe_reports_missing_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    company = _company()

    with connect(db_path) as connection:
        result = resolve_radar_universe(
            connection=connection,
            universe=(company,),
            as_of_date=AS_OF_DATE,
        )

    assert result.inputs == ()
    assert len(result.unresolved) == 1
    assert result.unresolved[0].company == company
    assert (
        result.unresolved[0].issue
        == RadarUniverseIssue.COMPANY_NOT_FOUND
    )


def test_resolve_radar_universe_reports_missing_forward_eps(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    company = _company()

    with connect(db_path) as connection:
        _insert_company(connection, company)

        result = resolve_radar_universe(
            connection=connection,
            universe=(company,),
            as_of_date=AS_OF_DATE,
        )

    assert result.inputs == ()
    assert len(result.unresolved) == 1
    assert result.unresolved[0].company == company
    assert (
        result.unresolved[0].issue
        == RadarUniverseIssue.FORWARD_EPS_PERIOD_NOT_FOUND
    )


def test_resolve_radar_universe_does_not_use_future_estimate(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    company = _company()

    with connect(db_path) as connection:
        company_id = _insert_company(
            connection,
            company,
        )
        _insert_eps_estimate(
            connection=connection,
            company_id=company_id,
            fiscal_period_end=date(2026, 12, 31),
            estimate_date=date(2026, 10, 1),
        )

        result = resolve_radar_universe(
            connection=connection,
            universe=(company,),
            as_of_date=AS_OF_DATE,
        )

    assert result.inputs == ()
    assert (
        result.unresolved[0].issue
        == RadarUniverseIssue.FORWARD_EPS_PERIOD_NOT_FOUND
    )


def test_resolve_radar_universe_handles_mixed_resolution(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    resolved = _company("AAA")
    missing_estimate = _company("BBB")
    missing_company = _company("CCC")

    with connect(db_path) as connection:
        resolved_id = _insert_company(
            connection,
            resolved,
        )
        _insert_company(
            connection,
            missing_estimate,
        )

        _insert_eps_estimate(
            connection=connection,
            company_id=resolved_id,
            fiscal_period_end=date(2026, 12, 31),
            estimate_date=date(2026, 9, 1),
        )

        result = resolve_radar_universe(
            connection=connection,
            universe=(
                resolved,
                missing_estimate,
                missing_company,
            ),
            as_of_date=AS_OF_DATE,
        )

    assert [
        item.company_id
        for item in result.inputs
    ] == [resolved_id]

    assert [
        item.company.ticker
        for item in result.unresolved
    ] == [
        "BBB",
        "CCC",
    ]

    assert [
        item.issue
        for item in result.unresolved
    ] == [
        RadarUniverseIssue.FORWARD_EPS_PERIOD_NOT_FOUND,
        RadarUniverseIssue.COMPANY_NOT_FOUND,
    ]


def test_resolve_radar_universe_rejects_duplicate_identity(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    first = _company(
        ticker="TEST",
        exchange="BME",
    )
    duplicate = CompanyConfig(
        name="Other Name",
        ticker="test",
        symbol="OTHER.MC",
        exchange="bme",
        currency="EUR",
    )

    with connect(db_path) as connection:
        with pytest.raises(
            ValueError,
            match="must be unique",
        ):
            resolve_radar_universe(
                connection=connection,
                universe=(first, duplicate),
                as_of_date=AS_OF_DATE,
            )


def test_resolve_radar_universe_accepts_empty_universe(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        result = resolve_radar_universe(
            connection=connection,
            universe=(),
            as_of_date=AS_OF_DATE,
        )

    assert result.inputs == ()
    assert result.unresolved == ()
