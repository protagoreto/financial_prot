from datetime import date

from src.ai import (
    AIAnalysisContext,
    AIValueScenario,
    build_ai_analysis_context,
)
from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import RadarEntry, RadarScenario
from src.value import ValueCondition


def _entry() -> RadarEntry:
    return RadarEntry(
        company_id=1,
        name="Test Company",
        ticker="TEST",
        exchange="BME",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=(
            "positive_net_income",
            "positive_free_cash_flow",
        ),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            RadarScenario(
                name="Base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
            RadarScenario(
                name="Stress",
                expected_return=None,
                required_price=None,
                price_margin=None,
                condition=ValueCondition.UNKNOWN,
            ),
        ),
    )


def test_build_ai_analysis_context_preserves_identity():
    context = build_ai_analysis_context(_entry())

    assert context.company_id == 1
    assert context.name == "Test Company"
    assert context.ticker == "TEST"
    assert context.exchange == "BME"


def test_build_ai_analysis_context_preserves_point_in_time_fields():
    context = build_ai_analysis_context(_entry())

    assert context.as_of_date == date(2026, 9, 22)
    assert context.fiscal_period_end == date(
        2026,
        12,
        31,
    )
    assert (
        context.availability
        == AnalysisAvailability.COMPLETE
    )


def test_build_ai_analysis_context_preserves_assessment():
    context = build_ai_analysis_context(_entry())

    assert context.quality_level == AssessmentLevel.STRONG
    assert context.risk_level == RiskLevel.LOW
    assert context.value_trap_warning is False

    assert context.quality_reasons == (
        "positive_net_income",
        "positive_free_cash_flow",
    )
    assert context.risk_reasons == ()
    assert context.value_trap_reasons == ()


def test_build_ai_analysis_context_preserves_scenarios():
    context = build_ai_analysis_context(_entry())

    assert context.scenarios == (
        AIValueScenario(
            name="Base",
            expected_return=0.12,
            required_price=55.0,
            price_margin=0.10,
            condition=ValueCondition.TARGET_MET,
        ),
        AIValueScenario(
            name="Stress",
            expected_return=None,
            required_price=None,
            price_margin=None,
            condition=ValueCondition.UNKNOWN,
        ),
    )


def test_build_ai_analysis_context_preserves_missing_values():
    context = build_ai_analysis_context(_entry())

    stress = context.scenarios[1]

    assert stress.expected_return is None
    assert stress.required_price is None
    assert stress.price_margin is None
    assert stress.condition == ValueCondition.UNKNOWN


def test_ai_context_is_frozen():
    context = build_ai_analysis_context(_entry())

    try:
        context.company_id = 2
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "AI analysis context must be immutable."
        )


def test_ai_value_scenario_is_frozen():
    scenario = build_ai_analysis_context(
        _entry()
    ).scenarios[0]

    try:
        scenario.expected_return = 0.99
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "AI value scenario must be immutable."
        )


def test_ai_context_can_be_constructed_explicitly():
    context = AIAnalysisContext(
        company_id=1,
        name="Test Company",
        ticker=None,
        exchange=None,
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.INSUFFICIENT,
        quality_level=None,
        risk_level=None,
        value_trap_warning=None,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(),
    )

    assert context.ticker is None
    assert context.quality_level is None
    assert context.scenarios == ()


def test_ai_analysis_narrative_is_valid():
    from src.ai import AIAnalysisNarrative

    narrative = AIAnalysisNarrative(
        summary="The available analysis is complete.",
        quality_commentary="Quality signals are strong.",
        risk_commentary="Recorded risk signals are low.",
        valuation_commentary=(
            "The Base scenario meets the configured target."
        ),
        limitations=(
            "Narrative is limited to supplied analysis context.",
        ),
    )

    assert narrative.is_valid()


def test_ai_analysis_narrative_rejects_blank_required_text():
    from src.ai import AIAnalysisNarrative

    narrative = AIAnalysisNarrative(
        summary=" ",
        quality_commentary="Quality commentary.",
        risk_commentary="Risk commentary.",
        valuation_commentary="Valuation commentary.",
        limitations=(),
    )

    assert not narrative.is_valid()


def test_ai_analysis_narrative_rejects_blank_limitation():
    from src.ai import AIAnalysisNarrative

    narrative = AIAnalysisNarrative(
        summary="Summary.",
        quality_commentary="Quality commentary.",
        risk_commentary="Risk commentary.",
        valuation_commentary="Valuation commentary.",
        limitations=("",),
    )

    assert not narrative.is_valid()


def test_ai_analysis_narrative_is_frozen():
    from src.ai import AIAnalysisNarrative

    narrative = AIAnalysisNarrative(
        summary="Summary.",
        quality_commentary="Quality commentary.",
        risk_commentary="Risk commentary.",
        valuation_commentary="Valuation commentary.",
        limitations=(),
    )

    try:
        narrative.summary = "Changed"
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "AI analysis narrative must be immutable."
        )
