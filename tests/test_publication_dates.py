from datetime import date

import pytest

from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.publication_dates import apply_publication_date


def create_record() -> FinancialRecord:
    return FinancialRecord(
        company_id=1,
        statement_type=StatementType.INCOME_STATEMENT,
        metric=FinancialMetric.EPS,
        value=2.0,
        currency="EUR",
        period_end=date(2026, 1, 31),
        period_type=PeriodType.ANNUAL,
        publication_date=None,
    )


def test_apply_publication_date():
    record = create_record()

    enriched = apply_publication_date(
        record=record,
        publication_date=date(2026, 3, 11),
    )

    assert enriched.publication_date == date(
        2026,
        3,
        11,
    )


def test_apply_publication_date_does_not_modify_original():
    record = create_record()

    enriched = apply_publication_date(
        record=record,
        publication_date=date(2026, 3, 11),
    )

    assert record.publication_date is None
    assert enriched.publication_date == date(
        2026,
        3,
        11,
    )


def test_publication_date_cannot_precede_period_end():
    record = create_record()

    with pytest.raises(ValueError):
        apply_publication_date(
            record=record,
            publication_date=date(2026, 1, 30),
        )