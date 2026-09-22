import json
from datetime import date

from src.ai import (
    AIAnalysisContext,
    AIValueScenario,
)
from src.ai_serialization import (
    serialize_ai_analysis_context,
)
from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.value import ValueCondition


def _context() -> AIAnalysisContext:
    return AIAnalysisContext(
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
            AIValueScenario(
                name="Base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
        ),
    )


def test_serialize_ai_analysis_context_is_deterministic():
    context = _context()

    first = serialize_ai_analysis_context(context)
    second = serialize_ai_analysis_context(context)

    assert first == second


def test_serialize_ai_analysis_context_preserves_identity():
    serialized = serialize_ai_analysis_context(
        _context()
    )

    assert serialized["company"] == {
        "company_id": 1,
        "name": "Test Company",
        "ticker": "TEST",
        "exchange": "BME",
    }


def test_serialize_ai_analysis_context_preserves_point_in_time():
    serialized = serialize_ai_analysis_context(
        _context()
    )

    assert serialized["point_in_time"] == {
        "as_of_date": "2026-09-22",
        "fiscal_period_end": "2026-12-31",
    }


def test_serialize_ai_analysis_context_preserves_assessment():
    serialized = serialize_ai_analysis_context(
        _context()
    )

    analysis = serialized["analysis"]

    assert analysis["availability"] == "complete"
    assert analysis["quality"] == {
        "level": "strong",
        "reasons": [
            "positive_net_income",
            "positive_free_cash_flow",
        ],
    }
    assert analysis["risk"] == {
        "level": "low",
        "reasons": [],
    }
    assert analysis["value_trap"] == {
        "warning": False,
        "reasons": [],
    }


def test_serialize_ai_analysis_context_preserves_scenarios():
    serialized = serialize_ai_analysis_context(
        _context()
    )

    assert serialized["analysis"]["scenarios"] == [
        {
            "name": "Base",
            "expected_return": 0.12,
            "required_price": 55.0,
            "price_margin": 0.10,
            "condition": "target_met",
        },
    ]


def test_serialize_ai_analysis_context_preserves_missing_values():
    context = AIAnalysisContext(
        company_id=2,
        name="Missing Data Company",
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
        scenarios=(
            AIValueScenario(
                name="Unknown",
                expected_return=None,
                required_price=None,
                price_margin=None,
                condition=ValueCondition.UNKNOWN,
            ),
        ),
    )

    serialized = serialize_ai_analysis_context(context)

    assert serialized["company"]["ticker"] is None
    assert serialized["company"]["exchange"] is None

    assert (
        serialized["analysis"]["quality"]["level"]
        is None
    )
    assert (
        serialized["analysis"]["risk"]["level"]
        is None
    )
    assert (
        serialized["analysis"]["value_trap"]["warning"]
        is None
    )

    scenario = serialized["analysis"]["scenarios"][0]

    assert scenario["expected_return"] is None
    assert scenario["required_price"] is None
    assert scenario["price_margin"] is None
    assert scenario["condition"] == "unknown"


def test_serialized_context_is_json_compatible():
    serialized = serialize_ai_analysis_context(
        _context()
    )

    encoded = json.dumps(
        serialized,
        sort_keys=True,
        separators=(",", ":"),
    )

    decoded = json.loads(encoded)

    assert decoded == serialized
