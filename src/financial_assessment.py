from src.assessment import (
    AssessmentLevel,
    AssessmentPolicy,
    FundamentalAssessment,
    RiskLevel,
)
from src.financial_signals import (
    FinancialFundamentalSignals,
)


def assess_financial_fundamentals(
    signals: FinancialFundamentalSignals,
    policy: AssessmentPolicy = AssessmentPolicy(),
) -> FundamentalAssessment | None:
    if not policy.is_valid():
        return None

    quality_checks = (
        (
            "positive_net_income",
            signals.positive_net_income,
        ),
        (
            "positive_roe",
            signals.positive_roe,
        ),
        (
            "positive_roa",
            signals.positive_roa,
        ),
        (
            "positive_tangible_book_growth",
            signals.positive_tangible_book_growth,
        ),
    )

    risk_checks = (
        (
            "revenue_decline",
            signals.revenue_decline,
        ),
        (
            "net_interest_income_decline",
            signals.net_interest_income_decline,
        ),
        (
            "eps_decline",
            signals.eps_decline,
        ),
        (
            "tangible_book_decline",
            signals.tangible_book_decline,
        ),
        (
            "share_dilution",
            signals.share_dilution,
        ),
    )

    known_quality = tuple(
        (name, value)
        for name, value in quality_checks
        if value is not None
    )

    positive_quality = tuple(
        name
        for name, value in known_quality
        if value is True
    )

    negative_quality = tuple(
        name
        for name, value in known_quality
        if value is False
    )

    known_risk = tuple(
        (name, value)
        for name, value in risk_checks
        if value is not None
    )

    active_risk = tuple(
        name
        for name, value in known_risk
        if value is True
    )

    quality_level = _classify_quality(
        known_count=len(known_quality),
        positive_count=len(positive_quality),
        minimum_positive=policy.min_quality_signals,
    )

    risk_level = _classify_risk(
        active_count=len(active_risk),
        low_maximum=(
            policy.max_risk_signals_for_low
        ),
        high_minimum=(
            policy.min_risk_signals_for_high
        ),
    )

    value_trap_reasons = active_risk

    return FundamentalAssessment(
        company_id=signals.company_id,
        quality_level=quality_level,
        risk_level=risk_level,
        value_trap_warning=(
            len(value_trap_reasons)
            >= policy.min_value_trap_warnings
        ),
        quality_reasons=(
            positive_quality + negative_quality
        ),
        risk_reasons=active_risk,
        value_trap_reasons=value_trap_reasons,
        known_quality_signals=len(
            known_quality
        ),
        positive_quality_signals=len(
            positive_quality
        ),
        known_risk_signals=len(
            known_risk
        ),
        active_risk_signals=len(
            active_risk
        ),
    )


def _classify_quality(
    known_count: int,
    positive_count: int,
    minimum_positive: int,
) -> AssessmentLevel:
    if known_count == 0:
        return AssessmentLevel.MIXED

    if positive_count >= minimum_positive:
        return AssessmentLevel.STRONG

    if positive_count == 0:
        return AssessmentLevel.WEAK

    return AssessmentLevel.MIXED


def _classify_risk(
    active_count: int,
    low_maximum: int,
    high_minimum: int,
) -> RiskLevel:
    if active_count <= low_maximum:
        return RiskLevel.LOW

    if active_count >= high_minimum:
        return RiskLevel.HIGH

    return RiskLevel.MODERATE
