from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.presentation import AnalysisPresentation
from src.presentation_text import render_analysis_text
from src.value import ValueCondition


def _presentation() -> AnalysisPresentation:
    return AnalysisPresentation(
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


def test_render_analysis_text_preserves_values():
    text = render_analysis_text(_presentation())

    assert "Test Company (TEST)" in text
    assert "As of: 2026-09-22" in text
    assert "Fiscal period end: 2026-12-31" in text
    assert "Availability: complete" in text
    assert "Quality: strong" in text
    assert "Risk: low" in text
    assert "Value trap warning: false" in text
    assert "Scenario: Base" in text
    assert "Expected return: 0.12" in text
    assert "Required price: 55.0" in text
    assert "Price margin: 0.1" in text
    assert "Value condition: target_met" in text
    assert "Target return: 0.1" in text
    assert "Horizon: 5 years" in text


def test_render_analysis_text_preserves_missing_values():
    presentation = AnalysisPresentation(
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

    text = render_analysis_text(presentation)

    assert text.startswith("Incomplete Company\n")
    assert "Availability: insufficient" in text
    assert "Quality: unavailable" in text
    assert "Risk: unavailable" in text
    assert "Value trap warning: unavailable" in text
    assert "Expected return: unavailable" in text
    assert "Required price: unavailable" in text
    assert "Price margin: unavailable" in text
    assert "Value condition: unavailable" in text


def test_render_analysis_text_does_not_create_recommendation():
    text = render_analysis_text(_presentation()).lower()

    assert "buy" not in text
    assert "sell" not in text
    assert "hold" not in text
