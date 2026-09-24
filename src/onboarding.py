from dataclasses import dataclass
from datetime import date
from enum import Enum
import sqlite3
from typing import Callable

from src.ingestion import (
    ingest_dividends,
    ingest_financials,
    ingest_forward_eps_estimate,
    ingest_prices_incremental,
    ingest_publication_dates,
)
from src.repository import get_company_by_id


class OnboardingStatus(str, Enum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True)
class OnboardingStepResult:
    name: str
    status: OnboardingStatus
    processed: int | None = None
    detail: str | None = None


@dataclass(frozen=True)
class CompanyOnboardingResult:
    company_id: int
    symbol: str
    steps: tuple[OnboardingStepResult, ...]

    @property
    def succeeded(self) -> int:
        return sum(
            step.status == OnboardingStatus.SUCCESS
            for step in self.steps
        )

    @property
    def unavailable(self) -> int:
        return sum(
            step.status == OnboardingStatus.UNAVAILABLE
            for step in self.steps
        )

    @property
    def failed(self) -> int:
        return sum(
            step.status == OnboardingStatus.FAILED
            for step in self.steps
        )


def _run_step(
    name: str,
    operation: Callable[[], int],
) -> OnboardingStepResult:
    try:
        processed = operation()
    except ValueError as exc:
        return OnboardingStepResult(
            name=name,
            status=OnboardingStatus.UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        return OnboardingStepResult(
            name=name,
            status=OnboardingStatus.FAILED,
            detail=f"{type(exc).__name__}: {exc}",
        )

    return OnboardingStepResult(
        name=name,
        status=OnboardingStatus.SUCCESS,
        processed=processed,
    )


def onboard_company(
    connection: sqlite3.Connection,
    company_id: int,
    price_provider,
    fundamentals_provider,
    estimate_provider,
    dividend_provider,
    initial_price_date: date,
    end_date: date,
    estimate_date: date | None = None,
    publication_date_provider=None,
) -> CompanyOnboardingResult:
    if company_id <= 0:
        raise ValueError("company_id must be positive")

    if initial_price_date > end_date:
        raise ValueError(
            "initial_price_date cannot be after end_date"
        )

    company = get_company_by_id(
        connection,
        company_id,
    )

    if company is None:
        raise ValueError(
            f"Company not found: {company_id}"
        )

    if company.symbol is None or not company.symbol.strip():
        raise ValueError(
            f"Company {company_id} has no provider symbol"
        )

    if company.currency is None or not company.currency.strip():
        raise ValueError(
            f"Company {company_id} has no currency"
        )

    symbol = company.symbol.strip()
    currency = company.currency.strip()

    steps = (
        _run_step(
            "prices",
            lambda: ingest_prices_incremental(
                connection=connection,
                provider=price_provider,
                company_id=company_id,
                symbol=symbol,
                currency=currency,
                initial_start_date=initial_price_date,
                end_date=end_date,
            ),
        ),
        _run_step(
            "financials",
            lambda: ingest_financials(
                connection=connection,
                provider=fundamentals_provider,
                company_id=company_id,
                symbol=symbol,
                currency=currency,
                fundamental_profile=(
                    company.fundamental_profile.value
                ),
            ),
        ),
        _run_step(
            "forward_eps",
            lambda: ingest_forward_eps_estimate(
                connection=connection,
                provider=estimate_provider,
                company_id=company_id,
                symbol=symbol,
                estimate_date=estimate_date,
            ),
        ),
        _run_step(
            "dividends",
            lambda: ingest_dividends(
                connection=connection,
                provider=dividend_provider,
                company_id=company_id,
                symbol=symbol,
                currency=currency,
            ),
        ),
        (
            _run_step(
                "publication_dates",
                lambda: ingest_publication_dates(
                    connection=connection,
                    provider=publication_date_provider,
                    company_id=company_id,
                    symbol=symbol,
                ),
            )
            if publication_date_provider is not None
            else OnboardingStepResult(
                name="publication_dates",
                status=OnboardingStatus.UNAVAILABLE,
                detail="Publication date provider not configured",
            )
        ),
    )

    return CompanyOnboardingResult(
        company_id=company_id,
        symbol=symbol,
        steps=steps,
    )
