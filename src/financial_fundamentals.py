from dataclasses import dataclass
from datetime import date
import sqlite3

from src.calculations import (
    compound_annual_growth_rate,
    growth_rate,
    return_on_equity,
)
from src.metrics import FinancialMetric, PeriodType
from src.repository import (
    get_financial_for_period_on_or_before,
    get_latest_financial_on_or_before,
)


FINANCIAL_REQUIRED_METRICS = (
    FinancialMetric.REVENUE,
    FinancialMetric.NET_INTEREST_INCOME,
    FinancialMetric.NET_INCOME,
    FinancialMetric.EPS,
    FinancialMetric.SHARES_OUTSTANDING,
    FinancialMetric.EQUITY,
    FinancialMetric.TANGIBLE_BOOK_VALUE,
    FinancialMetric.TOTAL_ASSETS,
    FinancialMetric.NET_LOANS,
)


@dataclass(frozen=True)
class FinancialFundamentalSnapshot:
    company_id: int
    as_of_date: date

    period_end: date
    publication_date: date

    revenue: float
    net_interest_income: float
    net_income: float
    eps: float
    shares_outstanding: float

    equity: float
    tangible_book_value: float
    total_assets: float
    net_loans: float


@dataclass(frozen=True)
class FinancialFundamentalGrowthSnapshot:
    company_id: int
    as_of_date: date

    current_period_end: date
    previous_period_end: date
    current_publication_date: date

    years_between_periods: float
    is_annual_comparison: bool

    revenue_growth: float | None
    net_interest_income_growth: float | None
    net_income_growth: float | None
    eps_growth: float | None
    shares_growth: float | None
    tangible_book_value_growth: float | None
    total_assets_growth: float | None
    net_loans_growth: float | None

    revenue_cagr: float | None
    net_interest_income_cagr: float | None
    net_income_cagr: float | None
    eps_cagr: float | None
    shares_cagr: float | None
    tangible_book_value_cagr: float | None
    total_assets_cagr: float | None
    net_loans_cagr: float | None

    return_on_equity: float | None
    return_on_assets: float | None


def _return_on_assets(
    net_income: float,
    beginning_assets: float,
    ending_assets: float,
) -> float | None:
    average_assets = (
        beginning_assets + ending_assets
    ) / 2

    if average_assets <= 0:
        return None

    return net_income / average_assets


def build_financial_fundamental_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> FinancialFundamentalSnapshot | None:
    records = {
        metric: get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=metric,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
        for metric in FINANCIAL_REQUIRED_METRICS
    }

    if any(
        record is None
        for record in records.values()
    ):
        return None

    values = list(records.values())
    period_end = values[0].period_end

    if any(
        record.period_end != period_end
        for record in values
    ):
        return None

    publication_dates = [
        record.publication_date
        for record in values
    ]

    if any(
        publication_date is None
        for publication_date in publication_dates
    ):
        return None

    total_assets = records[
        FinancialMetric.TOTAL_ASSETS
    ].value

    net_income = records[
        FinancialMetric.NET_INCOME
    ].value

    return FinancialFundamentalSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        period_end=period_end,
        publication_date=max(publication_dates),
        revenue=records[
            FinancialMetric.REVENUE
        ].value,
        net_interest_income=records[
            FinancialMetric.NET_INTEREST_INCOME
        ].value,
        net_income=net_income,
        eps=records[
            FinancialMetric.EPS
        ].value,
        shares_outstanding=records[
            FinancialMetric.SHARES_OUTSTANDING
        ].value,
        equity=records[
            FinancialMetric.EQUITY
        ].value,
        tangible_book_value=records[
            FinancialMetric.TANGIBLE_BOOK_VALUE
        ].value,
        total_assets=total_assets,
        net_loans=records[
            FinancialMetric.NET_LOANS
        ].value,
    )


def build_financial_fundamental_growth_snapshot(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> FinancialFundamentalGrowthSnapshot | None:
    current = {
        metric: get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=metric,
            as_of_date=as_of_date,
            period_type=PeriodType.ANNUAL,
        )
        for metric in FINANCIAL_REQUIRED_METRICS
    }

    if any(
        record is None
        for record in current.values()
    ):
        return None

    current_values = list(current.values())
    current_period_end = (
        current_values[0].period_end
    )

    if any(
        record.period_end != current_period_end
        for record in current_values
    ):
        return None

    publication_dates = [
        record.publication_date
        for record in current_values
    ]

    if any(
        publication_date is None
        for publication_date in publication_dates
    ):
        return None

    previous_periods = connection.execute(
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

    previous = None
    previous_period_end = None

    for row in previous_periods:
        candidate_period = date.fromisoformat(
            row["period_end"]
        )

        candidate = {
            metric:
                get_financial_for_period_on_or_before(
                    connection=connection,
                    company_id=company_id,
                    metric=metric,
                    period_end=candidate_period,
                    as_of_date=as_of_date,
                    period_type=PeriodType.ANNUAL,
                )
            for metric in FINANCIAL_REQUIRED_METRICS
        }

        if all(
            record is not None
            for record in candidate.values()
        ):
            previous = candidate
            previous_period_end = candidate_period
            break

    if (
        previous is None
        or previous_period_end is None
    ):
        return None

    days_between = (
        current_period_end - previous_period_end
    ).days

    years_between = days_between / 365.2425

    is_annual = (
        0.90 <= years_between <= 1.10
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
            years=years_between,
        )

    roe = (
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
        if is_annual
        else None
    )

    roa = (
        _return_on_assets(
            net_income=current[
                FinancialMetric.NET_INCOME
            ].value,
            beginning_assets=previous[
                FinancialMetric.TOTAL_ASSETS
            ].value,
            ending_assets=current[
                FinancialMetric.TOTAL_ASSETS
            ].value,
        )
        if is_annual
        else None
    )

    return FinancialFundamentalGrowthSnapshot(
        company_id=company_id,
        as_of_date=as_of_date,
        current_period_end=current_period_end,
        previous_period_end=previous_period_end,
        current_publication_date=max(
            publication_dates
        ),
        years_between_periods=years_between,
        is_annual_comparison=is_annual,
        revenue_growth=period_growth(
            FinancialMetric.REVENUE
        ),
        net_interest_income_growth=period_growth(
            FinancialMetric.NET_INTEREST_INCOME
        ),
        net_income_growth=period_growth(
            FinancialMetric.NET_INCOME
        ),
        eps_growth=period_growth(
            FinancialMetric.EPS
        ),
        shares_growth=period_growth(
            FinancialMetric.SHARES_OUTSTANDING
        ),
        tangible_book_value_growth=period_growth(
            FinancialMetric.TANGIBLE_BOOK_VALUE
        ),
        total_assets_growth=period_growth(
            FinancialMetric.TOTAL_ASSETS
        ),
        net_loans_growth=period_growth(
            FinancialMetric.NET_LOANS
        ),
        revenue_cagr=period_cagr(
            FinancialMetric.REVENUE
        ),
        net_interest_income_cagr=period_cagr(
            FinancialMetric.NET_INTEREST_INCOME
        ),
        net_income_cagr=period_cagr(
            FinancialMetric.NET_INCOME
        ),
        eps_cagr=period_cagr(
            FinancialMetric.EPS
        ),
        shares_cagr=period_cagr(
            FinancialMetric.SHARES_OUTSTANDING
        ),
        tangible_book_value_cagr=period_cagr(
            FinancialMetric.TANGIBLE_BOOK_VALUE
        ),
        total_assets_cagr=period_cagr(
            FinancialMetric.TOTAL_ASSETS
        ),
        net_loans_cagr=period_cagr(
            FinancialMetric.NET_LOANS
        ),
        return_on_equity=roe,
        return_on_assets=roa,
    )
