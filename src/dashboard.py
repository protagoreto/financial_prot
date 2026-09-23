from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.automation import (
    RadarRunConfig,
    run_audited_radar,
)
from src.db import connect, initialize_database
from src.radar_presentation import (
    RadarPresentation,
    build_radar_presentation,
)
from src.radar_universe import RadarUniverseUnresolved
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


@dataclass(frozen=True)
class DashboardRadarResult:
    presentation: RadarPresentation
    unresolved: tuple[RadarUniverseUnresolved, ...]


def run_dashboard_radar(
    db_path: Path,
    universe: tuple[CompanyConfig, ...],
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    scenario_name: str,
    model_version: str,
    data_version: str,
    target_return: float = 0.10,
    years: int = 5,
    low_net_debt_threshold: float = 2.0,
) -> DashboardRadarResult:
    config = RadarRunConfig(
        universe=universe,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
        low_net_debt_threshold=low_net_debt_threshold,
    )

    initialize_database(db_path)

    with connect(db_path) as connection:
        result = run_audited_radar(
            connection=connection,
            config=config,
            as_of_date=as_of_date,
            model_version=model_version,
            data_version=data_version,
        )

    presentation = build_radar_presentation(
        snapshot=result.snapshot,
        scenario_name=scenario_name,
    )

    return DashboardRadarResult(
        presentation=presentation,
        unresolved=result.unresolved,
    )
