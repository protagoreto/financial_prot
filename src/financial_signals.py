from dataclasses import dataclass
from datetime import date
import sqlite3

from src.financial_fundamentals import (
    build_financial_fundamental_growth_snapshot,
    build_financial_fundamental_snapshot,
)


@dataclass(frozen=True)
class FinancialFundamentalSignals:
    company_id: int
    as_of_date: date
    period_end: date

    # Quality.
    positive_net_income: bool
    positive_roe: bool | None
    positive_roa: bool | None
    positive_tangible_book_growth: bool | None

    # Deterioration / value-trap warnings.
    revenue_decline: bool | None
    net_interest_income_decline: bool | None
    eps_decline: bool | None
    tangible_book_decline: bool | None
    share_dilution: bool | None


def build_financial_fundamental_signals(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> FinancialFundamentalSignals | None:
    current = build_financial_fundamental_snapshot(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    growth = (
        build_financial_fundamental_growth_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=as_of_date,
        )
    )

    if current is None or growth is None:
        return None

    if (
        current.period_end
        != growth.current_period_end
    ):
        return None

    return FinancialFundamentalSignals(
        company_id=company_id,
        as_of_date=as_of_date,
        period_end=current.period_end,
        positive_net_income=(
            current.net_income > 0
        ),
        positive_roe=_is_positive(
            growth.return_on_equity
        ),
        positive_roa=_is_positive(
            growth.return_on_assets
        ),
        positive_tangible_book_growth=(
            _is_positive(
                growth.tangible_book_value_cagr
            )
        ),
        revenue_decline=_is_negative(
            growth.revenue_cagr
        ),
        net_interest_income_decline=(
            _is_negative(
                growth.net_interest_income_cagr
            )
        ),
        eps_decline=_is_negative(
            growth.eps_cagr
        ),
        tangible_book_decline=_is_negative(
            growth.tangible_book_value_cagr
        ),
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
