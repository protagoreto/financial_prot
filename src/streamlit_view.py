from dataclasses import asdict
from typing import Any

from src.presentation import AnalysisPresentation
from src.radar_presentation import RadarPresentation
from src.radar_universe import RadarUniverseUnresolved


def build_radar_table(
    presentation: RadarPresentation,
) -> list[dict[str, Any]]:
    return [
        build_analysis_row(analysis)
        for analysis in presentation.analyses
    ]


def build_analysis_row(
    analysis: AnalysisPresentation,
) -> dict[str, Any]:
    values = asdict(analysis)

    return {
        "Company": values["name"],
        "Ticker": values["ticker"],
        "Exchange": values["exchange"],
        "Availability": analysis.availability.value,
        "Quality": (
            analysis.quality_level.value
            if analysis.quality_level is not None
            else None
        ),
        "Risk": (
            analysis.risk_level.value
            if analysis.risk_level is not None
            else None
        ),
        "Value trap": analysis.value_trap_warning,
        "Scenario": analysis.scenario_name,
        "Expected return": analysis.expected_return,
        "Required price": analysis.required_price,
        "Price margin": analysis.price_margin,
        "Condition": (
            analysis.condition.value
            if analysis.condition is not None
            else None
        ),
    }


def build_unresolved_table(
    unresolved: tuple[RadarUniverseUnresolved, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "Company": item.company.name,
            "Ticker": item.company.ticker,
            "Exchange": item.company.exchange,
            "Issue": item.issue.value,
        }
        for item in unresolved
    ]
