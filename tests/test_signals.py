from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.repository import insert_financial_record
from src.signals import build_fundamental_signals


STATEMENT_TYPES = {
    FinancialMetric.REVENUE: (
        StatementType.INCOME_STATEMENT
    ),
    FinancialMetric.EBITDA: (
        StatementType.INCOME_STATEMENT
    ),
    FinancialMetric.EBIT: (
        StatementType.INCOME_STATEMENT
    ),
    FinancialMetric.NET_INCOME: (
        StatementType.INCOME_STATEMENT
    ),
    FinancialMetric.OPERATING_CASH_FLOW: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.CAPEX: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.FREE_CASH_FLOW: (
        StatementType.CASH_FLOW
    ),
    FinancialMetric.CASH: (
        StatementType.BALANCE_SHEET
    ),
    FinancialMetric.TOTAL_DEBT: (
        StatementType.BALANCE_SHEET
    ),
    FinancialMetric.EPS: (
        StatementType.PER_SHARE
    ),
    FinancialMetric.SHARES_OUTSTANDING: (
        StatementType.PER_SHARE
    ),
    FinancialMetric.EQUITY: (
        StatementType.BALANCE_SHEET
    ),
}


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


def insert_period(
    connection,
    company_id: int,
    period_end: str,
    publication_date: str,
    values: dict[FinancialMetric, float],
) -> None:
    for metric, value in values.items():
        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=STATEMENT_TYPES[
                    metric
                ],
                metric=metric,
                value=value,
                currency="EUR",
                period_end=period_end,
                period_type=PeriodType.ANNUAL,
                publication_date=publication_date,
            ),
        )


def previous_values():
    return {
        FinancialMetric.REVENUE: 1_000.0,
        FinancialMetric.EBITDA: 200.0,
        FinancialMetric.EBIT: 150.0,
        FinancialMetric.NET_INCOME: 100.0,
        FinancialMetric.OPERATING_CASH_FLOW: 180.0,
        FinancialMetric.CAPEX: 50.0,
        FinancialMetric.FREE_CASH_FLOW: 130.0,
        FinancialMetric.CASH: 300.0,
        FinancialMetric.TOTAL_DEBT: 400.0,
        FinancialMetric.EPS: 2.0,
        FinancialMetric.SHARES_OUTSTANDING: 50.0,
        FinancialMetric.EQUITY: 500.0,
    }


def healthy_current_values():
    return {
        FinancialMetric.REVENUE: 1_100.0,
        FinancialMetric.EBITDA: 240.0,
        FinancialMetric.EBIT: 176.0,
        FinancialMetric.NET_INCOME: 120.0,
        FinancialMetric.OPERATING_CASH_FLOW: 210.0,
        FinancialMetric.CAPEX: 50.0,
        FinancialMetric.FREE_CASH_FLOW: 160.0,
        FinancialMetric.CASH: 350.0,
        FinancialMetric.TOTAL_DEBT: 450.0,
        FinancialMetric.EPS: 2.5,
        FinancialMetric.SHARES_OUTSTANDING: 48.0,
        FinancialMetric.EQUITY: 550.0,
    }


def deteriorating_current_values():
    return {
        FinancialMetric.REVENUE: 900.0,
        FinancialMetric.EBITDA: 150.0,
        FinancialMetric.EBIT: 90.0,
        FinancialMetric.NET_INCOME: 60.0,
        FinancialMetric.OPERATING_CASH_FLOW: 110.0,
        FinancialMetric.CAPEX: 50.0,
        FinancialMetric.FREE_CASH_FLOW: 60.0,
        FinancialMetric.CASH: 100.0,
        FinancialMetric.TOTAL_DEBT: 500.0,
        FinancialMetric.EPS: 1.5,
        FinancialMetric.SHARES_OUTSTANDING: 55.0,
        FinancialMetric.EQUITY: 450.0,
    }


def build_test_database(
    tmp_path: Path,
    current_values,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    connection = connect(db_path)
    company_id = create_company(connection)

    insert_period(
        connection=connection,
        company_id=company_id,
        period_end="2024-12-31",
        publication_date="2025-02-20",
        values=previous_values(),
    )

    insert_period(
        connection=connection,
        company_id=company_id,
        period_end="2025-12-31",
        publication_date="2026-02-20",
        values=current_values,
    )

    return connection, company_id


def test_healthy_company_signals(
    tmp_path: Path,
):
    connection, company_id = build_test_database(
        tmp_path=tmp_path,
        current_values=healthy_current_values(),
    )

    try:
        signals = build_fundamental_signals(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )
    finally:
        connection.close()

    assert signals is not None

    assert signals.positive_net_income is True
    assert signals.positive_free_cash_flow is True
    assert signals.positive_roe is True
    assert signals.low_net_debt is True

    assert signals.revenue_decline is False
    assert signals.eps_decline is False
    assert (
        signals.free_cash_flow_decline
        is False
    )
    assert signals.margin_contraction is False
    assert signals.share_dilution is False


def test_deteriorating_company_signals(
    tmp_path: Path,
):
    connection, company_id = build_test_database(
        tmp_path=tmp_path,
        current_values=(
            deteriorating_current_values()
        ),
    )

    try:
        signals = build_fundamental_signals(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
        )
    finally:
        connection.close()

    assert signals is not None

    assert signals.positive_net_income is True
    assert signals.positive_free_cash_flow is True
    assert signals.positive_roe is True
    assert signals.low_net_debt is False

    assert signals.revenue_decline is True
    assert signals.eps_decline is True
    assert (
        signals.free_cash_flow_decline
        is True
    )
    assert signals.margin_contraction is True
    assert signals.share_dilution is True


def test_signals_respect_point_in_time(
    tmp_path: Path,
):
    connection, company_id = build_test_database(
        tmp_path=tmp_path,
        current_values=healthy_current_values(),
    )

    try:
        before = build_fundamental_signals(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 2, 19),
        )

        on_publication = (
            build_fundamental_signals(
                connection=connection,
                company_id=company_id,
                as_of_date=date(2026, 2, 20),
            )
        )
    finally:
        connection.close()

    assert before is None
    assert on_publication is not None


def test_signals_reject_negative_debt_threshold(
    tmp_path: Path,
):
    connection, company_id = build_test_database(
        tmp_path=tmp_path,
        current_values=healthy_current_values(),
    )

    try:
        signals = build_fundamental_signals(
            connection=connection,
            company_id=company_id,
            as_of_date=date(2026, 3, 1),
            low_net_debt_threshold=-1.0,
        )
    finally:
        connection.close()

    assert signals is None


def test_low_net_debt_threshold_is_explicit(
    tmp_path: Path,
):
    values = healthy_current_values()

    values[FinancialMetric.CASH] = 100.0
    values[FinancialMetric.TOTAL_DEBT] = 580.0
    values[FinancialMetric.EBITDA] = 240.0

    connection, company_id = build_test_database(
        tmp_path=tmp_path,
        current_values=values,
    )

    try:
        default_signals = (
            build_fundamental_signals(
                connection=connection,
                company_id=company_id,
                as_of_date=date(2026, 3, 1),
            )
        )

        strict_signals = (
            build_fundamental_signals(
                connection=connection,
                company_id=company_id,
                as_of_date=date(2026, 3, 1),
                low_net_debt_threshold=1.0,
            )
        )
    finally:
        connection.close()

    assert default_signals is not None
    assert strict_signals is not None

    assert default_signals.low_net_debt is True
    assert strict_signals.low_net_debt is False