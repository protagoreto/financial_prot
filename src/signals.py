from dataclasses import dataclass
from datetime import date
import sqlite3

from src.fundamentals import (
    build_fundamental_growth_snapshot,
    build_fundamental_snapshot,
)
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_financial_for_period_on_or_before,
)


@dataclass(frozen=True)
class FundamentalSignals:
    company_id: int
    as_of_date: date
    period_end: date

    # Quality.
    positive_net_income: bool
    positive_free_cash_flow: bool
    positive_roe: bool | None
    low_net_debt: bool | None

    # Deterioration / value-trap warnings.
    revenue_decline: bool | None
    eps_decline: bool | None
    free_cash_flow_decline: bool | None
    margin_contraction: bool | None
    share_dilution: bool | None


def build_fundamental_signals(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
    low_net_debt_threshold: float = 2.0,
) -> FundamentalSignals | None:
    if low_net_debt_threshold < 0:
        return None

    current = build_fundamental_snapshot(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    growth = build_fundamental_growth_snapshot(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    if current is None or growth is None:
        return None

    if current.period_end != growth.current_period_end:
        return None

    previous_revenue = (
        get_financial_for_period_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.REVENUE,
            period_end=growth.previous_period_end,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
    )

    previous_ebit = (
        get_financial_for_period_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EBIT,
            period_end=growth.previous_period_end,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
    )

    previous_ebit_margin = None

    if (
        previous_revenue is not None
        and previous_ebit is not None
        and previous_revenue.value > 0
    ):
        previous_ebit_margin = (
            previous_ebit.value
            / previous_revenue.value
        )

    margin_contraction = None

    if (
        current.ebit_margin is not None
        and previous_ebit_margin is not None
    ):
        margin_contraction = (
            current.ebit_margin
            < previous_ebit_margin
        )

    return FundamentalSignals(
        company_id=company_id,
        as_of_date=as_of_date,
        period_end=current.period_end,
        positive_net_income=(
            current.net_income > 0
        ),
        positive_free_cash_flow=(
            current.free_cash_flow > 0
        ),
        positive_roe=_is_positive(
            growth.return_on_equity
        ),
        low_net_debt=_at_or_below(
            current.net_debt_to_ebitda,
            low_net_debt_threshold,
        ),
        revenue_decline=_is_negative(
            growth.revenue_cagr
        ),
        eps_decline=_is_negative(
            growth.eps_cagr
        ),
        free_cash_flow_decline=_is_negative(
            growth.free_cash_flow_cagr
        ),
        margin_contraction=margin_contraction,
        share_dilution=_is_positive(
            growth.shares_cagr
        ),
    )


def _is_negative(
    value: float | None,
) -> bool | None:
    if value is None:
        return None

    return value < 0


def _is_positive(
    value: float | None,
) -> bool | None:
    if value is None:
        return None

    return value > 0


def _at_or_below(
    value: float | None,
    threshold: float,
) -> bool | None:
    if value is None:
        return None

    return value <= threshold