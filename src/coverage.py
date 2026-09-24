from dataclasses import dataclass
from datetime import date
import sqlite3

from src.financial_fundamentals import (
    FINANCIAL_REQUIRED_METRICS,
    build_financial_fundamental_growth_snapshot,
    build_financial_fundamental_snapshot,
)
from src.fundamentals import (
    build_fundamental_growth_snapshot,
    build_fundamental_snapshot,
)
from src.investment import AnalysisAvailability
from src.metrics import FinancialMetric
from src.repository import (
    get_company_by_id,
    get_next_estimate_period_on_or_after,
    get_price_on_or_before,
)


FUNDAMENTAL_SNAPSHOT_METRICS = (
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

FUNDAMENTAL_GROWTH_METRICS = (
    FinancialMetric.REVENUE,
    FinancialMetric.EBITDA,
    FinancialMetric.EBIT,
    FinancialMetric.NET_INCOME,
    FinancialMetric.EPS,
    FinancialMetric.FREE_CASH_FLOW,
    FinancialMetric.SHARES_OUTSTANDING,
    FinancialMetric.EQUITY,
)


@dataclass(frozen=True)
class CompanyCoverage:
    company_id: int
    as_of_date: date
    price_available: bool
    fundamental_snapshot_available: bool
    fundamental_growth_available: bool
    forward_eps_period: date | None
    estimate_count: int
    dividend_count: int
    missing_snapshot_metrics: tuple[FinancialMetric, ...]
    missing_growth_metrics: tuple[FinancialMetric, ...]

    @property
    def fundamentals_available(self) -> bool:
        return (
            self.fundamental_snapshot_available
            and self.fundamental_growth_available
        )

    @property
    def valuation_inputs_available(self) -> bool:
        return (
            self.price_available
            and self.forward_eps_period is not None
        )

    @property
    def availability(self) -> AnalysisAvailability:
        if (
            self.valuation_inputs_available
            and self.fundamentals_available
        ):
            return AnalysisAvailability.COMPLETE

        if self.valuation_inputs_available:
            return AnalysisAvailability.VALUATION_ONLY

        if self.fundamentals_available:
            return AnalysisAvailability.FUNDAMENTALS_ONLY

        return AnalysisAvailability.INSUFFICIENT


def build_company_coverage(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> CompanyCoverage:
    if company_id <= 0:
        raise ValueError(
            "company_id must be greater than zero."
        )

    company = get_company_by_id(
        connection=connection,
        company_id=company_id,
    )

    if company is None:
        raise ValueError(
            "Coverage company does not exist."
        )

    price = get_price_on_or_before(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    if company.fundamental_profile.value == "financial":
        fundamental_snapshot = (
            build_financial_fundamental_snapshot(
                connection=connection,
                company_id=company_id,
                as_of_date=as_of_date,
            )
        )

        fundamental_growth = (
            build_financial_fundamental_growth_snapshot(
                connection=connection,
                company_id=company_id,
                as_of_date=as_of_date,
            )
        )

        snapshot_metrics = FINANCIAL_REQUIRED_METRICS
        growth_metrics = FINANCIAL_REQUIRED_METRICS
    else:
        fundamental_snapshot = build_fundamental_snapshot(
            connection=connection,
            company_id=company_id,
            as_of_date=as_of_date,
        )

        fundamental_growth = (
            build_fundamental_growth_snapshot(
                connection=connection,
                company_id=company_id,
                as_of_date=as_of_date,
            )
        )

        snapshot_metrics = FUNDAMENTAL_SNAPSHOT_METRICS
        growth_metrics = FUNDAMENTAL_GROWTH_METRICS

    forward_eps_period = get_next_estimate_period_on_or_after(
        connection=connection,
        company_id=company_id,
        metric=FinancialMetric.EPS,
        as_of_date=as_of_date,
    )

    estimate_count = _count_rows_on_or_before(
        connection=connection,
        table="estimates",
        company_id=company_id,
        date_column="estimate_date",
        as_of_date=as_of_date,
    )

    dividend_count = _count_rows_on_or_before(
        connection=connection,
        table="dividends",
        company_id=company_id,
        date_column="ex_date",
        as_of_date=as_of_date,
    )

    available_metrics = _get_available_financial_metrics(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    missing_snapshot_metrics = tuple(
        metric
        for metric in snapshot_metrics
        if metric not in available_metrics
    )

    missing_growth_metrics = tuple(
        metric
        for metric in growth_metrics
        if metric not in available_metrics
    )

    return CompanyCoverage(
        company_id=company_id,
        as_of_date=as_of_date,
        price_available=price is not None,
        fundamental_snapshot_available=(
            fundamental_snapshot is not None
        ),
        fundamental_growth_available=(
            fundamental_growth is not None
        ),
        forward_eps_period=forward_eps_period,
        estimate_count=estimate_count,
        dividend_count=dividend_count,
        missing_snapshot_metrics=missing_snapshot_metrics,
        missing_growth_metrics=missing_growth_metrics,
    )


def _get_available_financial_metrics(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
) -> frozenset[FinancialMetric]:
    rows = connection.execute(
        """
        SELECT DISTINCT f.metric
        FROM financials AS f
        WHERE f.company_id = ?
        AND COALESCE(
            f.publication_date,
            (
                SELECT MIN(pd.publication_date)
                FROM publication_dates AS pd
                WHERE pd.company_id = f.company_id
                AND pd.period_end = f.period_end
                AND pd.period_type = f.period_type
            )
        ) <= ?
        """,
        (
            company_id,
            as_of_date.isoformat(),
        ),
    ).fetchall()

    return frozenset(
        FinancialMetric(row[0])
        for row in rows
    )


def _count_rows_on_or_before(
    connection: sqlite3.Connection,
    table: str,
    company_id: int,
    date_column: str,
    as_of_date: date,
) -> int:
    allowed = {
        ("estimates", "estimate_date"),
        ("dividends", "ex_date"),
    }

    if (table, date_column) not in allowed:
        raise ValueError(
            "Unsupported coverage count."
        )

    row = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE company_id = ?
        AND {date_column} <= ?
        """,
        (
            company_id,
            as_of_date.isoformat(),
        ),
    ).fetchone()

    return int(row[0])
