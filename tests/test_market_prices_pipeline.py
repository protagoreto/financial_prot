from datetime import date

from src.pipeline.market_prices import INITIAL_START_DATE


def test_initial_start_date_is_defined():
    assert isinstance(INITIAL_START_DATE, date)


def test_initial_start_date_precedes_2026():
    assert INITIAL_START_DATE < date(2026, 1, 1)