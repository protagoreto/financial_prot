from datetime import date, datetime, timezone

import pandas as pd
import yfinance as yf

from src.metrics import FinancialMetric
from src.models import EstimateRecord


class YahooEstimateProvider:
    @property
    def name(self) -> str:
        return "yahoo"

    def get_forward_eps_estimate(
        self,
        company_id: int,
        symbol: str,
        estimate_date: date | None = None,
    ) -> EstimateRecord:
        ticker = yf.Ticker(symbol)

        estimates = ticker.earnings_estimate
        info = ticker.info

        if estimates is None or estimates.empty:
            raise ValueError(
                f"{symbol}: earnings estimates unavailable"
            )

        if "+1y" not in estimates.index:
            raise ValueError(
                f"{symbol}: +1y EPS estimate unavailable"
            )

        row = estimates.loc["+1y"]

        value = row.get("avg")
        if value is None or pd.isna(value):
            raise ValueError(
                f"{symbol}: +1y average EPS unavailable"
            )

        fiscal_timestamp = info.get("nextFiscalYearEnd")
        if fiscal_timestamp is None:
            raise ValueError(
                f"{symbol}: next fiscal year end unavailable"
            )

        fiscal_period_end = datetime.fromtimestamp(
            fiscal_timestamp,
            tz=timezone.utc,
        ).date()

        analyst_count = row.get("numberOfAnalysts")
        if analyst_count is not None and pd.isna(analyst_count):
            analyst_count = None

        currency = row.get("currency")
        if currency is not None and pd.isna(currency):
            currency = None

        observation_date = (
            estimate_date
            if estimate_date is not None
            else datetime.now(timezone.utc).date()
        )

        if fiscal_period_end < observation_date:
            raise ValueError(
                f"{symbol}: next fiscal year end precedes "
                "estimate date"
            )

        return EstimateRecord(
            company_id=company_id,
            metric=FinancialMetric.EPS,
            value=float(value),
            currency=(
                str(currency)
                if currency is not None
                else None
            ),
            fiscal_period_end=fiscal_period_end,
            estimate_date=observation_date,
            analyst_count=(
                int(analyst_count)
                if analyst_count is not None
                else None
            ),
        )
