from datetime import date

import pandas as pd
import pytest

from src.models import PriceRecord
from src.providers.yahoo import YahooPriceProvider


def test_yahoo_provider_name():
    provider = YahooPriceProvider()

    assert provider.name == "yahoo"


def test_yahoo_normalizes_dataframe():
    provider = YahooPriceProvider()

    dataframe = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.5],
            "Close": [11.0, 12.5],
            "Adj Close": [10.8, 12.3],
            "Volume": [1000, 1200],
        },
        index=pd.to_datetime(
            [
                "2026-09-17",
                "2026-09-18",
            ]
        ),
    )

    records = provider.normalize_prices(
        company_id=1,
        dataframe=dataframe,
    )

    assert len(records) == 2
    assert isinstance(records[0], PriceRecord)

    assert records[0].price_date == date(2026, 9, 17)
    assert records[0].open == 10.0
    assert records[0].close == 11.0
    assert records[0].adjusted_close == 10.8

    assert records[1].price_date == date(2026, 9, 18)
    assert records[1].close == 12.5


def test_yahoo_empty_dataframe_returns_empty_list():
    provider = YahooPriceProvider()

    dataframe = pd.DataFrame()

    records = provider.normalize_prices(
        company_id=1,
        dataframe=dataframe,
    )

    assert records == []


def test_yahoo_rejects_invalid_date_range():
    provider = YahooPriceProvider()

    with pytest.raises(ValueError):
        provider.get_prices(
            company_id=1,
            symbol="TEST",
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 18),
        )