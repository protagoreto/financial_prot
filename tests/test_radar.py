from datetime import date
from unittest.mock import patch

import pytest

from src.assessment import (
    AssessmentLevel,
    FundamentalAssessment,
    RiskLevel,
)
from src.investment import (
    AnalysisAvailability,
    InvestmentAnalysis,
)
from src.radar import (
    RadarCompanyInput,
    build_radar_snapshot,
)
from src.scenarios import ValuationScenario
from src.value import (
    ScenarioValueAssessment,
    ValueAssessment,
    ValueCondition,
)


AS_OF_DATE = date(2026, 9, 21)
FISCAL_PERIOD_END = date(2026, 12, 31)


def _scenario() -> ValuationScenario:
    return ValuationScenario(
        name="base",
        eps_growth=0.05,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )


def _complete_analysis(
    company_id: int,
) -> InvestmentAnalysis:
    fundamentals = FundamentalAssessment(
        company_id=company_id,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=("positive_net_income",),
        risk_reasons=(),
        value_trap_reasons=(),
        known_quality_signals=4,
        positive_quality_signals=4,
        known_risk_signals=4,
        active_risk_signals=0,
    )

    value = ValueAssessment(
        target_return=0.10,
        scenarios=(
            ScenarioValueAssessment(
                name="base",
                target_return=0.10,
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
                condition=ValueCondition.TARGET_MET,
            ),
        ),
    )

    return InvestmentAnalysis(
        company_id=company_id,
        as_of_date=AS_OF_DATE,
        availability=AnalysisAvailability.COMPLETE,
        valuation=None,
        value=value,
        fundamentals=fundamentals,
    )


def test_radar_preserves_company_order():
    companies = (
        RadarCompanyInput(
            company_id=2,
            fiscal_period_end=FISCAL_PERIOD_END,
        ),
        RadarCompanyInput(
            company_id=1,
            fiscal_period_end=FISCAL_PERIOD_END,
        ),
    )

    def fake_analysis(**kwargs):
        return _complete_analysis(
            kwargs["company_id"]
        )

    with patch(
        "src.radar.build_investment_analysis",
        side_effect=fake_analysis,
    ):
        snapshot = build_radar_snapshot(
            connection=None,
            companies=companies,
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    assert [
        entry.company_id
        for entry in snapshot.entries
    ] == [2, 1]


def test_radar_exposes_fundamental_assessment():
    with patch(
        "src.radar.build_investment_analysis",
        return_value=_complete_analysis(1),
    ):
        snapshot = build_radar_snapshot(
            connection=None,
            companies=(
                RadarCompanyInput(
                    company_id=1,
                    fiscal_period_end=FISCAL_PERIOD_END,
                ),
            ),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    entry = snapshot.entries[0]

    assert entry.availability == AnalysisAvailability.COMPLETE
    assert entry.quality_level == AssessmentLevel.STRONG
    assert entry.risk_level == RiskLevel.LOW
    assert entry.value_trap_warning is False
    assert entry.quality_reasons == (
        "positive_net_income",
    )


def test_radar_exposes_value_scenarios():
    with patch(
        "src.radar.build_investment_analysis",
        return_value=_complete_analysis(1),
    ):
        snapshot = build_radar_snapshot(
            connection=None,
            companies=(
                RadarCompanyInput(
                    company_id=1,
                    fiscal_period_end=FISCAL_PERIOD_END,
                ),
            ),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    scenario = snapshot.entries[0].scenarios[0]

    assert scenario.name == "base"
    assert scenario.expected_return == pytest.approx(0.12)
    assert scenario.required_price == pytest.approx(55.0)
    assert scenario.price_margin == pytest.approx(0.10)
    assert scenario.condition == ValueCondition.TARGET_MET


def test_radar_handles_insufficient_analysis():
    analysis = InvestmentAnalysis(
        company_id=1,
        as_of_date=AS_OF_DATE,
        availability=AnalysisAvailability.INSUFFICIENT,
        valuation=None,
        value=None,
        fundamentals=None,
    )

    with patch(
        "src.radar.build_investment_analysis",
        return_value=analysis,
    ):
        snapshot = build_radar_snapshot(
            connection=None,
            companies=(
                RadarCompanyInput(
                    company_id=1,
                    fiscal_period_end=FISCAL_PERIOD_END,
                ),
            ),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    entry = snapshot.entries[0]

    assert entry.availability == AnalysisAvailability.INSUFFICIENT
    assert entry.quality_level is None
    assert entry.risk_level is None
    assert entry.value_trap_warning is None
    assert entry.quality_reasons == ()
    assert entry.risk_reasons == ()
    assert entry.value_trap_reasons == ()
    assert entry.scenarios == ()


def test_radar_rejects_duplicate_companies():
    companies = (
        RadarCompanyInput(
            company_id=1,
            fiscal_period_end=FISCAL_PERIOD_END,
        ),
        RadarCompanyInput(
            company_id=1,
            fiscal_period_end=date(2027, 12, 31),
        ),
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        build_radar_snapshot(
            connection=None,
            companies=companies,
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )


def test_radar_rejects_invalid_company_id():
    with pytest.raises(
        ValueError,
        match="company_id",
    ):
        build_radar_snapshot(
            connection=None,
            companies=(
                RadarCompanyInput(
                    company_id=0,
                    fiscal_period_end=FISCAL_PERIOD_END,
                ),
            ),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )


def test_radar_rejects_invalid_years():
    with pytest.raises(
        ValueError,
        match="years",
    ):
        build_radar_snapshot(
            connection=None,
            companies=(),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
            years=0,
        )


def test_radar_rejects_invalid_target_return():
    with pytest.raises(
        ValueError,
        match="target_return",
    ):
        build_radar_snapshot(
            connection=None,
            companies=(),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
            target_return=-1.0,
        )