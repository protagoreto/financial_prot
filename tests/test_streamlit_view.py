from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.presentation import AnalysisPresentation
from src.radar_presentation import RadarPresentation
from src.streamlit_view import build_radar_table
from src.value import ValueCondition


def test_build_radar_table_preserves_values():
    analysis = AnalysisPresentation(
        company_id=1,
        name="Example Company",
        ticker="EX",
        exchange="TEST",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        scenario_name="Base",
        expected_return=0.123456,
        required_price=101.2345,
        price_margin=0.06789,
        condition=ValueCondition.TARGET_MET,
    )

    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(analysis,),
    )

    rows = build_radar_table(
        presentation
    )

    assert rows == [
        {
            "Company": "Example Company",
            "Ticker": "EX",
            "Exchange": "TEST",
            "Availability": "complete",
            "Quality": "strong",
            "Risk": "low",
            "Value trap": False,
            "Scenario": "Base",
            "Expected return": 0.123456,
            "Required price": 101.2345,
            "Price margin": 0.06789,
            "Condition": "target_met",
        }
    ]


def test_build_radar_table_preserves_missing_values():
    analysis = AnalysisPresentation(
        company_id=1,
        name="Example Company",
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

    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(analysis,),
    )

    rows = build_radar_table(
        presentation
    )

    row = rows[0]

    assert row["Ticker"] is None
    assert row["Exchange"] is None
    assert row["Quality"] is None
    assert row["Risk"] is None
    assert row["Value trap"] is None
    assert row["Expected return"] is None
    assert row["Required price"] is None
    assert row["Price margin"] is None
    assert row["Condition"] is None


def test_build_radar_table_handles_empty_radar():
    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(),
    )

    assert build_radar_table(
        presentation
    ) == []


def test_build_unresolved_table_preserves_issue():
    from src.radar_universe import (
        RadarUniverseIssue,
        RadarUniverseUnresolved,
    )
    from src.streamlit_view import build_unresolved_table
    from src.universe import CompanyConfig

    company = CompanyConfig(
        name="Example Company",
        ticker="EX",
        symbol="EX",
        exchange="TEST",
        currency="EUR",
    )

    unresolved = (
        RadarUniverseUnresolved(
            company=company,
            issue=(
                RadarUniverseIssue
                .FORWARD_EPS_PERIOD_NOT_FOUND
            ),
        ),
    )

    assert build_unresolved_table(unresolved) == [
        {
            "Company": "Example Company",
            "Ticker": "EX",
            "Exchange": "TEST",
            "Issue": "forward_eps_period_not_found",
        }
    ]


def test_build_unresolved_table_handles_empty_input():
    from src.streamlit_view import build_unresolved_table

    assert build_unresolved_table(()) == []
