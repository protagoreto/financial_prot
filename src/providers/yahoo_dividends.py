import pandas as pd
import yfinance as yf

from src.models import DividendRecord


class YahooDividendProvider:
    @property
    def name(self) -> str:
        return "yahoo"

    def get_dividends(
        self,
        company_id: int,
        symbol: str,
        currency: str,
    ) -> list[DividendRecord]:
        dividends = yf.Ticker(symbol).dividends

        if dividends is None or dividends.empty:
            return []

        records: list[DividendRecord] = []

        for timestamp, value in dividends.items():
            if value is None or pd.isna(value):
                continue

            amount = float(value)

            if amount <= 0:
                continue

            records.append(
                DividendRecord(
                    company_id=company_id,
                    ex_date=timestamp.date(),
                    amount=amount,
                    currency=currency,
                )
            )

        return records
