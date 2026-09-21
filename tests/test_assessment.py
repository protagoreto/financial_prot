from datetime import date

from src.assessment import (
    AssessmentLevel,
    AssessmentPolicy,
    RiskLevel,
    assess_fundamentals,
)
from src.signals import FundamentalSignals


def make_signals(
    **overrides,
) -> FundamentalSignals:
    values = {
        "company_id": 1,
        "as_of_date": date(2026, 3, 1),
        "period_end": date(2025, 12, 31),
        "positive_net_income": True,
        "positive_free_cash_flow": True,
        "positive_roe": True,
        "low_net_debt": True,
        "revenue_decline": False,
        "eps_decline": False,
        "free_cash_flow_decline": False,
        "margin_contraction": False,
        "share_dilution": False,
    }

    values.update(overrides)

    return FundamentalSignals(**values)


def test_healthy_company_assessment():
    assessment = assess_fundamentals(
        make_signals()
    )

    assert assessment is not None

    assert (
        assessment.quality_level
        == AssessmentLevel.STRONG
    )
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.value_trap_warning is False

    assert assessment.known_quality_signals == 4
    assert assessment.positive_quality_signals == 4

    assert assessment.known_risk_signals == 5
    assert assessment.active_risk_signals == 0

    assert assessment.risk_reasons == ()
    assert assessment.value_trap_reasons == ()


def test_deteriorating_company_assessment():
    assessment = assess_fundamentals(
        make_signals(
            low_net_debt=False,
            revenue_decline=True,
            eps_decline=True,
            free_cash_flow_decline=True,
            margin_contraction=True,
            share_dilution=True,
        )
    )

    assert assessment is not None

    assert (
        assessment.quality_level
        == AssessmentLevel.STRONG
    )
    assert (
        assessment.risk_level
        == RiskLevel.HIGH
    )
    assert assessment.value_trap_warning is True

    assert assessment.active_risk_signals == 5

    assert assessment.risk_reasons == (
        "revenue_decline",
        "eps_decline",
        "free_cash_flow_decline",
        "margin_contraction",
        "share_dilution",
    )

    assert (
        assessment.value_trap_reasons
        == assessment.risk_reasons
    )


def test_single_warning_does_not_trigger_value_trap():
    assessment = assess_fundamentals(
        make_signals(
            eps_decline=True,
        )
    )

    assert assessment is not None

    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.value_trap_warning is False
    assert assessment.risk_reasons == (
        "eps_decline",
    )


def test_multiple_warnings_trigger_value_trap():
    assessment = assess_fundamentals(
        make_signals(
            eps_decline=True,
            margin_contraction=True,
        )
    )

    assert assessment is not None

    assert (
        assessment.risk_level
        == RiskLevel.MODERATE
    )
    assert assessment.value_trap_warning is True

    assert assessment.value_trap_reasons == (
        "eps_decline",
        "margin_contraction",
    )


def test_missing_signals_are_not_counted_as_failures():
    assessment = assess_fundamentals(
        make_signals(
            positive_roe=None,
            low_net_debt=None,
            revenue_decline=None,
            eps_decline=None,
        )
    )

    assert assessment is not None

    assert assessment.known_quality_signals == 2
    assert assessment.positive_quality_signals == 2

    assert (
        assessment.quality_level
        == AssessmentLevel.MIXED
    )

    assert assessment.known_risk_signals == 3
    assert assessment.active_risk_signals == 0
    assert assessment.risk_level == RiskLevel.LOW


def test_all_negative_quality_signals_are_weak():
    assessment = assess_fundamentals(
        make_signals(
            positive_net_income=False,
            positive_free_cash_flow=False,
            positive_roe=False,
            low_net_debt=False,
        )
    )

    assert assessment is not None

    assert (
        assessment.quality_level
        == AssessmentLevel.WEAK
    )
    assert assessment.positive_quality_signals == 0


def test_policy_changes_value_trap_threshold():
    signals = make_signals(
        eps_decline=True,
        margin_contraction=True,
    )

    default_assessment = assess_fundamentals(
        signals
    )

    strict_policy = AssessmentPolicy(
        min_value_trap_warnings=3,
    )

    strict_assessment = assess_fundamentals(
        signals,
        policy=strict_policy,
    )

    assert default_assessment is not None
    assert strict_assessment is not None

    assert (
        default_assessment.value_trap_warning
        is True
    )
    assert (
        strict_assessment.value_trap_warning
        is False
    )


def test_invalid_policy_is_rejected():
    policy = AssessmentPolicy(
        max_risk_signals_for_low=3,
        min_risk_signals_for_high=3,
    )

    assessment = assess_fundamentals(
        make_signals(),
        policy=policy,
    )

    assert assessment is None