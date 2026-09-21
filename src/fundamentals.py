from dataclasses import dataclass
from datetime import date
import sqlite3

from src.calculations import (
    calculate_net_debt,
    compound_annual_growth_rate,
    growth_rate,
    margin,
    net_debt_to_ebitda,
    return_on_equity,
)
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_financial_for_period_on_or_before,
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


@dataclass(frozen=True)
class FundamentalGrowthSnapshot:
    company_id: int
    as_of_date: date

    current_period_end: date
    previous_period_end: date
    current_publication_date: date

    years_between_periods: float
    is_annual_comparison: bool

    revenue_growth: float | None
    ebitda_growth: float | None
    ebit_growth: float | None
    net_income_growth: float | None
    eps_growth: float | None
    free_cash_flow_growth: float | None
    shares_growth: float | None

    revenue_cagr: float | None
    ebitda_cagr: float | None
    ebit_cagr: float | None
    net_income_cagr: float | None
    eps_cagr: float | None
    free_cash_flow_cagr: float | None
    shares_cagr: float | None

    return_on_equity: float | None


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


def build_fundamental_growth_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> FundamentalGrowthSnapshot | None:
    required_metrics = (
        FinancialMetric.REVENUE,
        FinancialMetric.EBITDA,
        FinancialMetric.EBIT,
        FinancialMetric.NET_INCOME,
        FinancialMetric.EPS,
        FinancialMetric.FREE_CASH_FLOW,
        FinancialMetric.SHARES_OUTSTANDING,
        FinancialMetric.EQUITY,
    )

    latest_records = {
        metric: get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=metric,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
        for metric in required_metrics
    }

    if any(
        record is None
        for record in latest_records.values()
    ):
        return None

    latest_values = list(latest_records.values())
    current_period_end = latest_values[0].period_end

    if any(
        record.period_end != current_period_end
        for record in latest_values
    ):
        return None

    current_publication_dates = [
        record.publication_date
        for record in latest_values
    ]

    if any(
        publication_date is None
        for publication_date in current_publication_dates
    ):
        return None

    previous_period_ends = connection.execute(
        """
        SELECT DISTINCT period_end
        FROM financials
        WHERE company_id = ?
        AND period_type = ?
        AND period_end < ?
        ORDER BY period_end DESC
        """,
        (
            company_id,
            PeriodType.ANNUAL.value,
            current_period_end.isoformat(),
        ),
    ).fetchall()

    for period_row in previous_period_ends:
        previous_period_end = date.fromisoformat(
            period_row["period_end"]
        )

        previous_records = {
            metric: get_financial_for_period_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=metric,
                period_end=previous_period_end,
                as_of_date=as_of_date,
                period_type=PeriodType.ANNUAL,
            )
            for metric in required_metrics
        }

        if all(
            record is not None
            for record in previous_records.values()
        ):
            break
    else:
        return None

    current = latest_records
    previous = previous_records

    days_between_periods = (
        current_period_end - previous_period_end
    ).days

    years_between_periods = (
        days_between_periods / 365.2425
    )

    is_annual_comparison = (
        0.90 <= years_between_periods <= 1.10
    )

    def period_growth(
        metric: FinancialMetric,
    ) -> float | None:
        return growth_rate(
            current_value=current[metric].value,
            previous_value=previous[metric].value,
        )

    def period_cagr(
        metric: FinancialMetric,
    ) -> float | None:
        return compound_annual_growth_rate(
            current_value=current[metric].value,
            previous_value=previous[metric].value,
            years=years_between_periods,
        )

    return FundamentalGrowthSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        current_period_end=current_period_end,
        previous_period_end=previous_period_end,
        current_publication_date=max(
            current_publication_dates
        ),
        years_between_periods=years_between_periods,
        is_annual_comparison=is_annual_comparison,
        revenue_growth=period_growth(
            FinancialMetric.REVENUE
        ),
        ebitda_growth=period_growth(
            FinancialMetric.EBITDA
        ),
        ebit_growth=period_growth(
            FinancialMetric.EBIT
        ),
        net_income_growth=period_growth(
            FinancialMetric.NET_INCOME
        ),
        eps_growth=period_growth(
            FinancialMetric.EPS
        ),
        free_cash_flow_growth=period_growth(
            FinancialMetric.FREE_CASH_FLOW
        ),
        shares_growth=period_growth(
            FinancialMetric.SHARES_OUTSTANDING
        ),
        revenue_cagr=period_cagr(
            FinancialMetric.REVENUE
        ),
        ebitda_cagr=period_cagr(
            FinancialMetric.EBITDA
        ),
        ebit_cagr=period_cagr(
            FinancialMetric.EBIT
        ),
        net_income_cagr=period_cagr(
            FinancialMetric.NET_INCOME
        ),
        eps_cagr=period_cagr(
            FinancialMetric.EPS
        ),
        free_cash_flow_cagr=period_cagr(
            FinancialMetric.FREE_CASH_FLOW
        ),
        shares_cagr=period_cagr(
            FinancialMetric.SHARES_OUTSTANDING
        ),
        return_on_equity=(
            return_on_equity(
                net_income=current[
                    FinancialMetric.NET_INCOME
                ].value,
                beginning_equity=previous[
                    FinancialMetric.EQUITY
                ].value,
                ending_equity=current[
                    FinancialMetric.EQUITY
                ].value,
            )
            if is_annual_comparison
            else None
        ),
    )