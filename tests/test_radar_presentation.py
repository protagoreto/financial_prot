from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import (
    RadarEntry,
    RadarScenario,
    RadarSnapshot,
)
from src.radar_presentation import build_radar_presentation
from src.value import ValueCondition


def test_build_radar_presentation():
    snapshot = RadarSnapshot(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        entries=(
            RadarEntry(
                company_id=1,
                name="Example Company",
                ticker="EX",
                exchange="TEST",
                as_of_date=date(2026, 9, 22),
                fiscal_period_end=date(2026, 12, 31),
                availability=AnalysisAvailability.COMPLETE,
                quality_level=AssessmentLevel.STRONG,
                risk_level=RiskLevel.LOW,
                value_trap_warning=False,
                quality_reasons=(),
                risk_reasons=(),
                value_trap_reasons=(),
                scenarios=(
                    RadarScenario(
                        name="Base",
                        expected_return=0.12,
                        required_price=100.0,
                        price_margin=0.05,
                        condition=ValueCondition.TARGET_MET,
                    ),
                    RadarScenario(
                        name="Stress",
                        expected_return=0.04,
                        required_price=70.0,
                        price_margin=-0.20,
                        condition=ValueCondition.TARGET_NOT_MET,
                    ),
                ),
            ),
        ),
    )

    presentation = build_radar_presentation(
        snapshot=snapshot,
        scenario_name="Base",
    )

    assert presentation.as_of_date == date(
        2026,
        9,
        22,
    )
    assert presentation.target_return == 0.10
    assert presentation.years == 5
    assert presentation.scenario_name == "Base"

    assert len(presentation.analyses) == 1

    analysis = presentation.analyses[0]

    assert analysis.company_id == 1
    assert analysis.name == "Example Company"
    assert analysis.scenario_name == "Base"
    assert analysis.expected_return == 0.12
    assert analysis.required_price == 100.0
    assert analysis.price_margin == 0.05
    assert analysis.condition == ValueCondition.TARGET_MET


def test_build_radar_presentation_preserves_missing_scenario():
    snapshot = RadarSnapshot(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        entries=(
            RadarEntry(
                company_id=1,
                name="Example Company",
                ticker="EX",
                exchange="TEST",
                as_of_date=date(2026, 9, 22),
                fiscal_period_end=date(2026, 12, 31),
                availability=AnalysisAvailability.COMPLETE,
                quality_level=None,
                risk_level=None,
                value_trap_warning=None,
                quality_reasons=(),
                risk_reasons=(),
                value_trap_reasons=(),
                scenarios=(),
            ),
        ),
    )

    presentation = build_radar_presentation(
        snapshot=snapshot,
        scenario_name="Base",
    )

    assert len(presentation.analyses) == 1

    analysis = presentation.analyses[0]

    assert analysis.scenario_name == "Base"
    assert analysis.expected_return is None
    assert analysis.required_price is None
    assert analysis.price_margin is None
    assert analysis.condition is None
