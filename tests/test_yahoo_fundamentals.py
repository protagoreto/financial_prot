from datetime import datetime

import pandas as pd

from src.metrics import (
    FinancialMetric,
    StatementType,
)
from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)


def test_normalize_income_statement():
    dataframe = pd.DataFrame(
        {
            datetime(2025, 12, 31): [
                1000.0,
                150.0,
                120.0,
                80.0,
                2.0,
            ],
        },
        index=[
    		"TotalRevenue",
    		"EBITDA",
    		"EBIT",
    		"NetIncome",
    		"DilutedEPS",
	    ],
    )

    provider = YahooFundamentalsProvider()

    records = provider.normalize_statement(
        company_id=1,
        dataframe=dataframe,
        statement_type=StatementType.INCOME_STATEMENT,
        metric_map=provider.INCOME_METRICS,
    )

    assert len(records) == 5

    values = {
        record.metric: record.value
        for record in records
    }

    assert values[FinancialMetric.REVENUE] == 1000.0
    assert values[FinancialMetric.EBITDA] == 150.0
    assert values[FinancialMetric.EBIT] == 120.0
    assert values[FinancialMetric.NET_INCOME] == 80.0
    assert values[FinancialMetric.EPS] == 2.0


def test_normalizer_skips_missing_values():
    dataframe = pd.DataFrame(
        {
            datetime(2025, 12, 31): [
                1000.0,
                float("nan"),
            ],
        },
        index=[
    		"TotalRevenue",
    		"EBITDA",
	    ],
    )

    provider = YahooFundamentalsProvider()

    records = provider.normalize_statement(
        company_id=1,
        dataframe=dataframe,
        statement_type=StatementType.INCOME_STATEMENT,
        metric_map=provider.INCOME_METRICS,
    )

    assert len(records) == 1
    assert records[0].metric == FinancialMetric.REVENUE


def test_normalizer_skips_unknown_metrics():
    dataframe = pd.DataFrame(
        {
            datetime(2025, 12, 31): [
                1000.0,
                999.0,
            ],
        },
        index=[
    		"TotalRevenue",
    		"UnknownYahooMetric",
        ],
    )

    provider = YahooFundamentalsProvider()

    records = provider.normalize_statement(
        company_id=1,
        dataframe=dataframe,
        statement_type=StatementType.INCOME_STATEMENT,
        metric_map=provider.INCOME_METRICS,
    )

    assert len(records) == 1
    assert records[0].metric == FinancialMetric.REVENUE


def test_normalized_records_do_not_invent_publication_date():
    dataframe = pd.DataFrame(
        {
            datetime(2025, 12, 31): [2.0],
        },
      	 index=[
    		"DilutedEPS",
        ],
    )

    provider = YahooFundamentalsProvider()

    records = provider.normalize_statement(
        company_id=1,
        dataframe=dataframe,
        statement_type=StatementType.INCOME_STATEMENT,
        metric_map=provider.INCOME_METRICS,
    )

    assert len(records) == 1
    assert records[0].publication_date is None

def test_supported_metric_maps_cover_core_financials():
    provider = YahooFundamentalsProvider()

    mapped_metrics = set(
        provider.INCOME_METRICS.values()
    )
    mapped_metrics.update(
        provider.BALANCE_METRICS.values()
    )
    mapped_metrics.update(
        provider.CASH_FLOW_METRICS.values()
    )

    expected_metrics = {
        FinancialMetric.REVENUE,
        FinancialMetric.EBITDA,
        FinancialMetric.EBIT,
        FinancialMetric.NET_INCOME,
        FinancialMetric.EPS,
        FinancialMetric.OPERATING_CASH_FLOW,
        FinancialMetric.CAPEX,
        FinancialMetric.FREE_CASH_FLOW,
        FinancialMetric.CASH,
        FinancialMetric.TOTAL_DEBT,
        FinancialMetric.EQUITY,
        FinancialMetric.SHARES_OUTSTANDING,
    }

    assert expected_metrics.issubset(
        mapped_metrics
    )

def test_capex_is_normalized_as_positive_investment():
    provider = YahooFundamentalsProvider()

    result = provider.normalize_metric_value(
        metric=FinancialMetric.CAPEX,
        value=-2_712_000_000.0,
    )

    assert result == 2_712_000_000.0


def test_non_capex_value_preserves_sign():
    provider = YahooFundamentalsProvider()

    result = provider.normalize_metric_value(
        metric=FinancialMetric.FREE_CASH_FLOW,
        value=-500_000_000.0,
    )

    assert result == -500_000_000.0