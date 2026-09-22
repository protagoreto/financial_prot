from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.presentation import (
    AnalysisPresentation,
    build_analysis_presentation,
)
from src.radar_report import RadarReportRow
from src.value import ValueCondition


def _row() -> RadarReportRow:
    return RadarReportRow(
        company_id=1,
        name="Test Company",
        ticker="TEST",
        exchange="BME",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        scenario_name="Base",
        expected_return=0.12,
        required_price=55.0,
        price_margin=0.10,
        condition=ValueCondition.TARGET_MET,
    )


def test_build_analysis_presentation():
    row = _row()

    presentation = build_analysis_presentation(row)

    assert isinstance(
        presentation,
        AnalysisPresentation,
    )
    assert presentation.company_id == row.company_id
    assert presentation.name == row.name
    assert presentation.ticker == row.ticker
    assert presentation.exchange == row.exchange
    assert presentation.as_of_date == row.as_of_date
    assert (
        presentation.fiscal_period_end
        == row.fiscal_period_end
    )
    assert presentation.target_return == row.target_return
    assert presentation.years == row.years
    assert presentation.availability == row.availability
    assert presentation.quality_level == row.quality_level
    assert presentation.risk_level == row.risk_level
    assert (
        presentation.value_trap_warning
        == row.value_trap_warning
    )
    assert presentation.scenario_name == row.scenario_name
    assert (
        presentation.expected_return
        == row.expected_return
    )
    assert (
        presentation.required_price
        == row.required_price
    )
    assert presentation.price_margin == row.price_margin
    assert presentation.condition == row.condition


def test_build_analysis_presentation_preserves_missing_values():
    row = RadarReportRow(
        company_id=1,
        name="Incomplete Company",
        ticker=None,
        exchange=None,
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.INSUFFICIENT,
        quality_level=None,
        risk_level=None,
        value_trap_warning=None,
        scenario_name="Base",
        expected_return=None,
        required_price=None,
        price_margin=None,
        condition=None,
    )

    presentation = build_analysis_presentation(row)

    assert presentation.ticker is None
    assert presentation.exchange is None
    assert presentation.quality_level is None
    assert presentation.risk_level is None
    assert presentation.value_trap_warning is None
    assert presentation.expected_return is None
    assert presentation.required_price is None
    assert presentation.price_margin is None
    assert presentation.condition is None
