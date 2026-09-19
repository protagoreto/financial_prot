import pandas as pd
import yfinance as yf

from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)
from src.models import FinancialRecord
from src.providers.fundamentals_base import FundamentalsProvider


class YahooFundamentalsProvider(FundamentalsProvider):

    INCOME_METRICS = {
        "TotalRevenue": FinancialMetric.REVENUE,
        "EBITDA": FinancialMetric.EBITDA,
        "EBIT": FinancialMetric.EBIT,
        "NetIncome": FinancialMetric.NET_INCOME,
        "DilutedEPS": FinancialMetric.EPS,
    }

    BALANCE_METRICS = {
        "CashCashEquivalentsAndShortTermInvestments":
            FinancialMetric.CASH,
        "TotalDebt":
            FinancialMetric.TOTAL_DEBT,
        "StockholdersEquity":
            FinancialMetric.EQUITY,
        "OrdinarySharesNumber":
            FinancialMetric.SHARES_OUTSTANDING,
    }

    CASH_FLOW_METRICS = {
        "OperatingCashFlow":
            FinancialMetric.OPERATING_CASH_FLOW,
        "CapitalExpenditure":
            FinancialMetric.CAPEX,
        "FreeCashFlow":
            FinancialMetric.FREE_CASH_FLOW,
    }

    @property
    def name(self) -> str:
        return "yahoo"

    def get_annual_financials(
        self,
        company_id: int,
        symbol: str,
    ) -> list[FinancialRecord]:
        ticker = yf.Ticker(symbol)

        records: list[FinancialRecord] = []

        records.extend(
            self.normalize_statement(
                company_id=company_id,
                dataframe=ticker.get_income_stmt(
                    freq="yearly"
                ),
                statement_type=StatementType.INCOME_STATEMENT,
                metric_map=self.INCOME_METRICS,
            )
        )

        records.extend(
            self.normalize_statement(
                company_id=company_id,
                dataframe=ticker.get_balance_sheet(
                    freq="yearly"
                ),
                statement_type=StatementType.BALANCE_SHEET,
                metric_map=self.BALANCE_METRICS,
            )
        )

        records.extend(
            self.normalize_statement(
                company_id=company_id,
                dataframe=ticker.get_cash_flow(
                    freq="yearly"
                ),
                statement_type=StatementType.CASH_FLOW,
                metric_map=self.CASH_FLOW_METRICS,
            )
        )

        return records

    def normalize_statement(
        self,
        company_id: int,
        dataframe: pd.DataFrame,
        statement_type: StatementType,
        metric_map: dict[str, FinancialMetric],
    ) -> list[FinancialRecord]:
        if dataframe.empty:
            return []

        records: list[FinancialRecord] = []

        for yahoo_metric, metric in metric_map.items():
            if yahoo_metric not in dataframe.index:
                continue

            row = dataframe.loc[yahoo_metric]

            for period_end, value in row.items():
                if value is None or pd.isna(value):
                    continue

                records.append(
                    FinancialRecord(
                        company_id=company_id,
                        statement_type=statement_type,
                        metric=metric,
                        value=self.normalize_metric_value(
    			metric=metric,
    			value=float(value),
			),
                        period_end=period_end.date(),
                        period_type=PeriodType.ANNUAL,
                    )
                )

        return records

    @staticmethod
    def _optional_float(value):
        if value is None or pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def normalize_metric_value(
        metric: FinancialMetric,
        value: float,
    ) -> float:
        if metric == FinancialMetric.CAPEX:
            return abs(value)

        return value