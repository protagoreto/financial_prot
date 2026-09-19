from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.models import PriceRecord
from src.providers.base import PriceProvider


class YahooPriceProvider(PriceProvider):

    @property
    def name(self) -> str:
        return "yahoo"

    def get_prices(
        self,
        company_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceRecord]:
        if start_date > end_date:
            raise ValueError(
                "start_date cannot be later than end_date"
            )

        # Yahoo/yfinance treats end as exclusive.
        yahoo_end_date = end_date + timedelta(days=1)

        dataframe = yf.download(
            symbol,
            start=start_date.isoformat(),
            end=yahoo_end_date.isoformat(),
            auto_adjust=False,
            actions=False,
            progress=False,
        )

        return self.normalize_prices(
            company_id=company_id,
            dataframe=dataframe,
        )

    def normalize_prices(
        self,
        company_id: int,
        dataframe: pd.DataFrame,
    ) -> list[PriceRecord]:
        if dataframe.empty:
            return []

        dataframe = dataframe.copy()

        # yfinance can return MultiIndex columns even for one ticker.
        if isinstance(dataframe.columns, pd.MultiIndex):
            dataframe.columns = dataframe.columns.get_level_values(0)

        records: list[PriceRecord] = []

        for index, row in dataframe.iterrows():
            record = PriceRecord(
                company_id=company_id,
                price_date=index.date(),
                open=self._optional_float(row.get("Open")),
                high=self._optional_float(row.get("High")),
                low=self._optional_float(row.get("Low")),
                close=float(row["Close"]),
                adjusted_close=self._optional_float(
                    row.get("Adj Close")
                ),
                volume=self._optional_float(row.get("Volume")),
            )

            records.append(record)

        return records

    @staticmethod
    def _optional_float(value):
        if value is None or pd.isna(value):
            return None

        return float(value)