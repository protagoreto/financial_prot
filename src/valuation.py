from dataclasses import dataclass
from datetime import date

import sqlite3

from src.calculations import earnings_yield, price_to_earnings
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_latest_estimate_on_or_before,
    get_latest_financial_on_or_before,
    get_price_on_or_before,
)

@dataclass(frozen=True)
class ValuationSnapshot:
    company_id: int
    as_of_date: date

    price_date: date
    price: float

    eps_period_end: date
    eps_publication_date: date
    eps: float

    pe: float | None
    earnings_yield: float | None


def build_valuation_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> ValuationSnapshot | None:
    price = get_price_on_or_before(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    eps = get_latest_financial_on_or_before(
        connection=connection,
        company_id=company_id,
        metric=FinancialMetric.EPS,
        as_of_date=as_of_date,
        period_type=PeriodType.ANNUAL,
    )

    if price is None or eps is None:
        return None

    if eps.publication_date is None:
        return None

    return ValuationSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        price_date=price.price_date,
        price=price.close,
        eps_period_end=eps.period_end,
        eps_publication_date=eps.publication_date,
        eps=eps.value,
        pe=price_to_earnings(
            price=price.close,
            eps=eps.value,
        ),
        earnings_yield=earnings_yield(
            price=price.close,
            eps=eps.value,
        ),
    )

@dataclass(frozen=True)
class ForwardValuationSnapshot:
    company_id: int
    as_of_date: date

    price_date: date
    price: float

    fiscal_period_end: date
    estimate_date: date
    analyst_count: int | None
    forward_eps: float

    forward_pe: float | None
    forward_earnings_yield: float | None

def build_forward_valuation_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
    fiscal_period_end: date,
) -> ForwardValuationSnapshot | None:
    price = get_price_on_or_before(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    estimate = get_latest_estimate_on_or_before(
        connection=connection,
        company_id=company_id,
        metric=FinancialMetric.EPS,
        fiscal_period_end=fiscal_period_end,
        as_of_date=as_of_date,
    )

    if price is None or estimate is None:
        return None

    return ForwardValuationSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        price_date=price.price_date,
        price=price.close,
        fiscal_period_end=estimate.fiscal_period_end,
        estimate_date=estimate.estimate_date,
        analyst_count=estimate.analyst_count,
        forward_eps=estimate.value,
        forward_pe=price_to_earnings(
            price=price.close,
            eps=estimate.value,
        ),
        forward_earnings_yield=earnings_yield(
            price=price.close,
            eps=estimate.value,
        ),
    )

