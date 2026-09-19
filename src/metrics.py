from enum import Enum


class FinancialMetric(str, Enum):
    # Income statement
    REVENUE = "revenue"
    EBITDA = "ebitda"
    EBIT = "ebit"
    NET_INCOME = "net_income"
    EPS = "eps"

    # Cash flow
    OPERATING_CASH_FLOW = "operating_cash_flow"
    CAPEX = "capex"
    FREE_CASH_FLOW = "free_cash_flow"

    # Balance sheet
    CASH = "cash"
    TOTAL_DEBT = "total_debt"
    NET_DEBT = "net_debt"
    EQUITY = "equity"

    # Share data
    SHARES_OUTSTANDING = "shares_outstanding"


class StatementType(str, Enum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    PER_SHARE = "per_share"


class PeriodType(str, Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"