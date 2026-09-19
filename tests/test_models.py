import pytest
from pydantic import ValidationError

from src.models import EstimateRecord, FinancialRecord


def test_valid_financial_record():
    record = FinancialRecord(
        company_id=1,
        statement_type="income_statement",
        metric="net_income",
        value=100.0,
        currency="EUR",
        period_start="2025-01-01",
        period_end="2025-12-31",
        period_type="annual",
        publication_date="2026-02-01",
        source_id=1,
    )

    assert record.metric.value == "net_income"
    assert record.value == 100.0


def test_financial_record_rejects_invalid_period():
    with pytest.raises(ValidationError):
        FinancialRecord(
            company_id=1,
            statement_type="income_statement",
            metric="revenue",
            value=100.0,
            period_start="2026-01-01",
            period_end="2025-12-31",
            period_type="annual",
        )


def test_financial_record_rejects_invalid_publication_date():
    with pytest.raises(ValidationError):
        FinancialRecord(
            company_id=1,
            statement_type="income_statement",
            metric="revenue",
            value=100.0,
            period_end="2025-12-31",
            period_type="annual",
            publication_date="2025-01-01",
        )


def test_valid_estimate_record():
    record = EstimateRecord(
        company_id=1,
        metric="eps",
        value=2.50,
        currency="EUR",
        fiscal_period_end="2027-12-31",
        estimate_date="2026-09-19",
        analyst_count=12,
        source_id=1,
    )

    assert record.metric.value == "eps"
    assert record.analyst_count == 12


def test_estimate_rejects_negative_analyst_count():
    with pytest.raises(ValidationError):
        EstimateRecord(
            company_id=1,
            metric="eps",
            value=2.50,
            fiscal_period_end="2027-12-31",
            estimate_date="2026-09-19",
            analyst_count=-1,
        )