from dataclasses import dataclass
from datetime import date

from src.presentation import (
    AnalysisPresentation,
    build_analysis_presentation,
)
from src.radar_report import build_radar_report
from src.radar import RadarSnapshot


@dataclass(frozen=True)
class RadarPresentation:
    as_of_date: date
    target_return: float
    years: int
    scenario_name: str
    analyses: tuple[AnalysisPresentation, ...]


def build_radar_presentation(
    snapshot: RadarSnapshot,
    scenario_name: str,
) -> RadarPresentation:
    rows = build_radar_report(
        snapshot=snapshot,
        scenario_name=scenario_name,
    )

    analyses = tuple(
        build_analysis_presentation(row)
        for row in rows
    )

    return RadarPresentation(
        as_of_date=snapshot.as_of_date,
        target_return=snapshot.target_return,
        years=snapshot.years,
        scenario_name=scenario_name,
        analyses=analyses,
    )
