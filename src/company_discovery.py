import sqlite3

from src.ingestion import get_or_create_company
from src.providers.discovery_base import (
    CompanyCandidate,
    CompanyDiscoveryProvider,
)
from src.universe import CompanyConfig


VALID_FUNDAMENTAL_PROFILES = frozenset(
    {"operating", "financial"}
)


def discover_companies(
    provider: CompanyDiscoveryProvider,
    query: str,
    max_results: int = 8,
) -> tuple[CompanyCandidate, ...]:
    return provider.search(
        query=query,
        max_results=max_results,
    )


def build_company_config(
    candidate: CompanyCandidate,
    exchange: str,
    fundamental_profile: str,
) -> CompanyConfig:
    normalized_exchange = exchange.strip().upper()
    normalized_profile = (
        fundamental_profile.strip().lower()
    )

    if not normalized_exchange:
        raise ValueError(
            "exchange cannot be empty."
        )

    if (
        normalized_profile
        not in VALID_FUNDAMENTAL_PROFILES
    ):
        raise ValueError(
            "fundamental_profile must be "
            "'operating' or 'financial'."
        )

    if not candidate.symbol.strip():
        raise ValueError(
            "candidate symbol cannot be empty."
        )

    if not candidate.name.strip():
        raise ValueError(
            "candidate name cannot be empty."
        )

    if not candidate.currency:
        raise ValueError(
            "candidate currency is required before "
            "registration."
        )

    return CompanyConfig(
        name=candidate.name.strip(),
        ticker=_ticker_from_symbol(
            candidate.symbol
        ),
        symbol=candidate.symbol.strip(),
        exchange=normalized_exchange,
        currency=candidate.currency.strip().upper(),
        fundamental_profile=normalized_profile,
    )


def register_company_candidate(
    connection: sqlite3.Connection,
    candidate: CompanyCandidate,
    exchange: str,
    fundamental_profile: str,
) -> tuple[int, CompanyConfig]:
    company = build_company_config(
        candidate=candidate,
        exchange=exchange,
        fundamental_profile=fundamental_profile,
    )

    company_id = get_or_create_company(
        connection=connection,
        name=company.name,
        ticker=company.ticker,
        exchange=company.exchange,
        currency=company.currency,
        fundamental_profile=(
            company.fundamental_profile
        ),
        symbol=company.symbol,
    )

    return company_id, company


def _ticker_from_symbol(symbol: str) -> str:
    normalized = symbol.strip()

    if not normalized:
        raise ValueError(
            "symbol cannot be empty."
        )

    return normalized.split(".", 1)[0].upper()
