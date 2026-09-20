from datetime import date

from src.models import FinancialRecord


def apply_publication_date(
    record: FinancialRecord,
    publication_date: date,
) -> FinancialRecord:
    """
    Return a copy of a financial record enriched with a
    verified publication date.

    The original record is not modified.
    """

    if publication_date < record.period_end:
        raise ValueError(
            "Publication date cannot be earlier "
            "than period end."
        )

    return record.model_copy(
        update={
            "publication_date": publication_date,
        }
    )