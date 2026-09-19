from datetime import date

import pytest

from src.models import PriceRecord
from src.providers.base import PriceProvider


class DummyPriceProvider(PriceProvider):

    @property
    def name(self) -> str:
        return "dummy"

    def get_prices(
        self,
        company_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceRecord]:

        return [
            PriceRecord(
                company_id=company_id,
                price_date=start_date,
                open=10.0,
                high=12.0,
                low=9.0,
                close=11.0,
                adjusted_close=11.0,
                volume=1000,
                currency="EUR",
            )
        ]


def test_price_provider_contract():
    provider = DummyPriceProvider()

    records = provider.get_prices(
        company_id=1,
        symbol="TEST",
        start_date=date(2026, 9, 18),
        end_date=date(2026, 9, 18),
    )

    assert provider.name == "dummy"
    assert len(records) == 1
    assert isinstance(records[0], PriceRecord)
    assert records[0].close == 11.0


def test_price_provider_is_abstract():
    with pytest.raises(TypeError):
        PriceProvider()