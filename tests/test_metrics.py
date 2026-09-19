from src.metrics import FinancialMetric, PeriodType, StatementType


def test_financial_metric_values():
    assert FinancialMetric.REVENUE.value == "revenue"
    assert FinancialMetric.NET_INCOME.value == "net_income"
    assert FinancialMetric.FREE_CASH_FLOW.value == "free_cash_flow"
    assert FinancialMetric.NET_DEBT.value == "net_debt"


def test_statement_types():
    assert StatementType.INCOME_STATEMENT.value == "income_statement"
    assert StatementType.BALANCE_SHEET.value == "balance_sheet"
    assert StatementType.CASH_FLOW.value == "cash_flow"
    assert StatementType.PER_SHARE.value == "per_share"


def test_period_types():
    assert PeriodType.ANNUAL.value == "annual"
    assert PeriodType.QUARTERLY.value == "quarterly"
    assert PeriodType.TTM.value == "ttm"