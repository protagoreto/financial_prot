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
            "Total Revenue",
            "EBITDA",
            "EBIT",
            "Net Income",
            "Diluted EPS",
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
            "Total Revenue",
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
            "Total Revenue",
            "Unknown Yahoo Metric",
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
            "Diluted EPS",
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