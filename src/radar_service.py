from dataclasses import dataclass
from datetime import date
import sqlite3

from src.assessment import AssessmentPolicy
from src.radar import (
    RadarSnapshot,
    build_radar_snapshot,
)
from src.radar_universe import (
    RadarUniverseUnresolved,
    resolve_radar_universe,
)
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


@dataclass(frozen=True)
class RadarRun:
    snapshot: RadarSnapshot
    unresolved: tuple[RadarUniverseUnresolved, ...]


def run_radar(
    connection: sqlite3.Connection,
    universe: tuple[CompanyConfig, ...],
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float = 0.10,
    years: int = 5,
    assessment_policy: AssessmentPolicy = AssessmentPolicy(),
    low_net_debt_threshold: float = 2.0,
) -> RadarRun:
    resolution = resolve_radar_universe(
        connection=connection,
        universe=universe,
        as_of_date=as_of_date,
    )

    snapshot = build_radar_snapshot(
        connection=connection,
        companies=resolution.inputs,
        as_of_date=as_of_date,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
        assessment_policy=assessment_policy,
        low_net_debt_threshold=low_net_debt_threshold,
    )

    return RadarRun(
        snapshot=snapshot,
        unresolved=resolution.unresolved,
    )
