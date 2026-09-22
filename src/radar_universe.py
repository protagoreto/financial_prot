from dataclasses import dataclass
from datetime import date
from enum import Enum
import sqlite3

from src.metrics import FinancialMetric
from src.radar import RadarCompanyInput
from src.repository import (
    get_company_id_by_ticker_exchange,
    get_next_estimate_period_on_or_after,
)
from src.universe import CompanyConfig


class RadarUniverseIssue(str, Enum):
    COMPANY_NOT_FOUND = "company_not_found"
    FORWARD_EPS_PERIOD_NOT_FOUND = (
        "forward_eps_period_not_found"
    )


@dataclass(frozen=True)
class RadarUniverseUnresolved:
    company: CompanyConfig
    issue: RadarUniverseIssue


@dataclass(frozen=True)
class RadarUniverseResolution:
    inputs: tuple[RadarCompanyInput, ...]
    unresolved: tuple[RadarUniverseUnresolved, ...]


def resolve_radar_universe(
    connection: sqlite3.Connection,
    universe: tuple[CompanyConfig, ...],
    as_of_date: date,
) -> RadarUniverseResolution:
    _validate_universe(universe)

    inputs: list[RadarCompanyInput] = []
    unresolved: list[RadarUniverseUnresolved] = []

    for company in universe:
        company_id = get_company_id_by_ticker_exchange(
            connection=connection,
            ticker=company.ticker,
            exchange=company.exchange,
        )

        if company_id is None:
            unresolved.append(
                RadarUniverseUnresolved(
                    company=company,
                    issue=RadarUniverseIssue.COMPANY_NOT_FOUND,
                )
            )
            continue

        fiscal_period_end = (
            get_next_estimate_period_on_or_after(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                as_of_date=as_of_date,
            )
        )

        if fiscal_period_end is None:
            unresolved.append(
                RadarUniverseUnresolved(
                    company=company,
                    issue=(
                        RadarUniverseIssue
                        .FORWARD_EPS_PERIOD_NOT_FOUND
                    ),
                )
            )
            continue

        inputs.append(
            RadarCompanyInput(
                company_id=company_id,
                fiscal_period_end=fiscal_period_end,
            )
        )

    return RadarUniverseResolution(
        inputs=tuple(inputs),
        unresolved=tuple(unresolved),
    )


def _validate_universe(
    universe: tuple[CompanyConfig, ...],
) -> None:
    identities = [
        (
            company.ticker.strip().upper(),
            company.exchange.strip().upper(),
        )
        for company in universe
    ]

    if any(
        not ticker or not exchange
        for ticker, exchange in identities
    ):
        raise ValueError(
            "Radar universe companies require ticker and exchange."
        )

    if len(identities) != len(set(identities)):
        raise ValueError(
            "Radar universe companies must be unique."
        )
