from dataclasses import dataclass
from datetime import date
import sqlite3

from src.calculations import (
    calculate_net_debt,
    margin,
    net_debt_to_ebitda,
)
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_latest_financial_on_or_before,
)


@dataclass(frozen=True)
class FundamentalSnapshot:
    company_id: int
    as_of_date: date

    period_end: date
    publication_date: date

    revenue: float
    ebitda: float
    ebit: float
    net_income: float
    operating_cash_flow: float
    capex: float
    free_cash_flow: float
    cash: float
    total_debt: float

    ebitda_margin: float | None
    ebit_margin: float | None
    net_margin: float | None
    fcf_margin: float | None

    net_debt: float | None
    net_debt_to_ebitda: float | None


def build_fundamental_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> FundamentalSnapshot | None:
    metrics = {
        metric: get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=metric,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
        for metric in (
            FinancialMetric.REVENUE,
            FinancialMetric.EBITDA,
            FinancialMetric.EBIT,
            FinancialMetric.NET_INCOME,
            FinancialMetric.OPERATING_CASH_FLOW,
            FinancialMetric.CAPEX,
            FinancialMetric.FREE_CASH_FLOW,
            FinancialMetric.CASH,
            FinancialMetric.TOTAL_DEBT,
        )
    }

    if any(
        record is None
        for record in metrics.values()
    ):
        return None

    records = list(metrics.values())

    period_end = records[0].period_end

    if any(
        record.period_end != period_end
        for record in records
    ):
        return None

    publication_dates = [
        record.publication_date
        for record in records
    ]

    if any(
        publication_date is None
        for publication_date in publication_dates
    ):
        return None

    publication_date = max(publication_dates)

    revenue = metrics[
        FinancialMetric.REVENUE
    ].value
    ebitda = metrics[
        FinancialMetric.EBITDA
    ].value
    ebit = metrics[
        FinancialMetric.EBIT
    ].value
    net_income = metrics[
        FinancialMetric.NET_INCOME
    ].value
    operating_cash_flow = metrics[
        FinancialMetric.OPERATING_CASH_FLOW
    ].value
    capex = metrics[
        FinancialMetric.CAPEX
    ].value
    free_cash_flow = metrics[
        FinancialMetric.FREE_CASH_FLOW
    ].value
    cash = metrics[
        FinancialMetric.CASH
    ].value
    total_debt = metrics[
        FinancialMetric.TOTAL_DEBT
    ].value

    net_debt = calculate_net_debt(
        total_debt=total_debt,
        cash=cash,
    )

    return FundamentalSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        period_end=period_end,
        publication_date=publication_date,
        revenue=revenue,
        ebitda=ebitda,
        ebit=ebit,
        net_income=net_income,
        operating_cash_flow=operating_cash_flow,
        capex=capex,
        free_cash_flow=free_cash_flow,
        cash=cash,
        total_debt=total_debt,
        ebitda_margin=margin(
            value=ebitda,
            revenue=revenue,
        ),
        ebit_margin=margin(
            value=ebit,
            revenue=revenue,
        ),
        net_margin=margin(
            value=net_income,
            revenue=revenue,
        ),
        fcf_margin=margin(
            value=free_cash_flow,
            revenue=revenue,
        ),
        net_debt=net_debt,
        net_debt_to_ebitda=(
            net_debt_to_ebitda(
                net_debt=net_debt,
                ebitda=ebitda,
            )
            if net_debt is not None
            else None
        ),
    )