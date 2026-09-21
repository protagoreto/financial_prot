from dataclasses import dataclass
from enum import Enum

from src.signals import FundamentalSignals


class AssessmentLevel(str, Enum):
    STRONG = "strong"
    MIXED = "mixed"
    WEAK = "weak"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class AssessmentPolicy:
    min_quality_signals: int = 3
    max_risk_signals_for_low: int = 1
    min_risk_signals_for_high: int = 3
    min_value_trap_warnings: int = 2

    def is_valid(self) -> bool:
        if self.min_quality_signals < 1:
            return False

        if self.max_risk_signals_for_low < 0:
            return False

        if self.min_risk_signals_for_high < 1:
            return False

        if (
            self.min_risk_signals_for_high
            <= self.max_risk_signals_for_low
        ):
            return False

        if self.min_value_trap_warnings < 1:
            return False

        return True


@dataclass(frozen=True)
class FundamentalAssessment:
    company_id: int

    quality_level: AssessmentLevel
    risk_level: RiskLevel
    value_trap_warning: bool

    quality_reasons: tuple[str, ...]
    risk_reasons: tuple[str, ...]
    value_trap_reasons: tuple[str, ...]

    known_quality_signals: int
    positive_quality_signals: int

    known_risk_signals: int
    active_risk_signals: int


def assess_fundamentals(
    signals: FundamentalSignals,
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
            "positive_free_cash_flow",
            signals.positive_free_cash_flow,
        ),
        (
            "positive_roe",
            signals.positive_roe,
        ),
        (
            "low_net_debt",
            signals.low_net_debt,
        ),
    )

    risk_checks = (
        (
            "revenue_decline",
            signals.revenue_decline,
        ),
        (
            "eps_decline",
            signals.eps_decline,
        ),
        (
            "free_cash_flow_decline",
            signals.free_cash_flow_decline,
        ),
        (
            "margin_contraction",
            signals.margin_contraction,
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

    value_trap_warning = (
        len(value_trap_reasons)
        >= policy.min_value_trap_warnings
    )

    return FundamentalAssessment(
        company_id=signals.company_id,
        quality_level=quality_level,
        risk_level=risk_level,
        value_trap_warning=value_trap_warning,
        quality_reasons=(
            positive_quality + negative_quality
        ),
        risk_reasons=active_risk,
        value_trap_reasons=value_trap_reasons,
        known_quality_signals=len(known_quality),
        positive_quality_signals=(
            len(positive_quality)
        ),
        known_risk_signals=len(known_risk),
        active_risk_signals=len(active_risk),
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