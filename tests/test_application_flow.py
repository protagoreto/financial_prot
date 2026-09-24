from datetime import date

import src.application_flow as flow
from src.coverage import CompanyCoverage
from src.investment import AnalysisAvailability
from src.onboarding import CompanyOnboardingResult
from src.providers.discovery_base import CompanyCandidate
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


SCENARIOS = (
    ValuationScenario(
        name="base",
        eps_growth=0.06,
        dividend_yield=0.03,
        terminal_pe=14.0,
    ),
)


def _candidate() -> CompanyCandidate:
    return CompanyCandidate(
        symbol="TEST",
        name="Test Company",
        currency="USD",
    )


def _company() -> CompanyConfig:
    return CompanyConfig(
        name="Test Company",
        ticker="TEST",
        symbol="TEST",
        exchange="NASDAQ",
        currency="USD",
        fundamental_profile="operating",
    )


def _coverage(
    forward_eps_period=date(2027, 6, 30),
) -> CompanyCoverage:
    return CompanyCoverage(
        company_id=7,
        as_of_date=date(2026, 9, 24),
        price_available=True,
        fundamental_snapshot_available=False,
        fundamental_growth_available=False,
        forward_eps_period=forward_eps_period,
        estimate_count=1 if forward_eps_period else 0,
        dividend_count=0,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )


def _onboarding() -> CompanyOnboardingResult:
    return CompanyOnboardingResult(
        company_id=7,
        symbol="TEST",
        steps=(),
    )


def test_flow_coordinates_registration_onboarding_and_analysis(
    monkeypatch,
):
    coverage = _coverage()
    onboarding = _onboarding()
    analysis = object()

    monkeypatch.setattr(
        flow,
        "register_company_candidate",
        lambda **kwargs: (7, _company()),
    )
    monkeypatch.setattr(
        flow,
        "onboard_company",
        lambda **kwargs: onboarding,
    )
    monkeypatch.setattr(
        flow,
        "build_company_coverage",
        lambda **kwargs: coverage,
    )
    monkeypatch.setattr(
        flow,
        "build_investment_analysis",
        lambda **kwargs: analysis,
    )

    result = flow.run_application_flow(
        connection=object(),
        candidate=_candidate(),
        exchange="NASDAQ",
        fundamental_profile="operating",
        price_provider=object(),
        fundamentals_provider=object(),
        estimate_provider=object(),
        dividend_provider=object(),
        initial_price_date=date(2024, 1, 1),
        end_date=date(2026, 9, 24),
        as_of_date=date(2026, 9, 24),
        scenarios=SCENARIOS,
    )

    assert result.company_id == 7
    assert result.company == _company()
    assert result.onboarding is onboarding
    assert result.coverage is coverage
    assert result.analysis is analysis

    assert result.radar_input is not None
    assert result.radar_input.company_id == 7
    assert (
        result.radar_input.fiscal_period_end
        == date(2027, 6, 30)
    )


def test_flow_without_forward_eps_skips_analysis_and_radar(
    monkeypatch,
):
    coverage = _coverage(forward_eps_period=None)

    monkeypatch.setattr(
        flow,
        "register_company_candidate",
        lambda **kwargs: (7, _company()),
    )
    monkeypatch.setattr(
        flow,
        "onboard_company",
        lambda **kwargs: _onboarding(),
    )
    monkeypatch.setattr(
        flow,
        "build_company_coverage",
        lambda **kwargs: coverage,
    )

    def unexpected_analysis(**kwargs):
        raise AssertionError(
            "analysis must not run without forward EPS"
        )

    monkeypatch.setattr(
        flow,
        "build_investment_analysis",
        unexpected_analysis,
    )

    result = flow.run_application_flow(
        connection=object(),
        candidate=_candidate(),
        exchange="NASDAQ",
        fundamental_profile="operating",
        price_provider=object(),
        fundamentals_provider=object(),
        estimate_provider=object(),
        dividend_provider=object(),
        initial_price_date=date(2024, 1, 1),
        end_date=date(2026, 9, 24),
        as_of_date=date(2026, 9, 24),
        scenarios=SCENARIOS,
    )

    assert result.analysis is None
    assert result.radar_input is None
    assert result.analysis_available is False
    assert result.radar_eligible is False


def test_flow_allows_partial_analysis(
    monkeypatch,
):
    coverage = _coverage()

    class PartialAnalysis:
        availability = AnalysisAvailability.VALUATION_ONLY

    monkeypatch.setattr(
        flow,
        "register_company_candidate",
        lambda **kwargs: (7, _company()),
    )
    monkeypatch.setattr(
        flow,
        "onboard_company",
        lambda **kwargs: _onboarding(),
    )
    monkeypatch.setattr(
        flow,
        "build_company_coverage",
        lambda **kwargs: coverage,
    )
    monkeypatch.setattr(
        flow,
        "build_investment_analysis",
        lambda **kwargs: PartialAnalysis(),
    )

    result = flow.run_application_flow(
        connection=object(),
        candidate=_candidate(),
        exchange="NASDAQ",
        fundamental_profile="operating",
        price_provider=object(),
        fundamentals_provider=object(),
        estimate_provider=object(),
        dividend_provider=object(),
        initial_price_date=date(2024, 1, 1),
        end_date=date(2026, 9, 24),
        as_of_date=date(2026, 9, 24),
        scenarios=SCENARIOS,
    )

    assert (
        flow.describe_analysis_state(result)
        == "valuation_only"
    )
    assert result.radar_eligible is True


def test_flow_validates_dates_before_registration(
    monkeypatch,
):
    called = False

    def register(**kwargs):
        nonlocal called
        called = True
        return 7, _company()

    monkeypatch.setattr(
        flow,
        "register_company_candidate",
        register,
    )

    try:
        flow.run_application_flow(
            connection=object(),
            candidate=_candidate(),
            exchange="NASDAQ",
            fundamental_profile="operating",
            price_provider=object(),
            fundamentals_provider=object(),
            estimate_provider=object(),
            dividend_provider=object(),
            initial_price_date=date(2026, 9, 25),
            end_date=date(2026, 9, 24),
            as_of_date=date(2026, 9, 24),
            scenarios=SCENARIOS,
        )
    except ValueError as exc:
        assert "initial_price_date" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert called is False


def test_flow_rejects_as_of_after_end_date(
    monkeypatch,
):
    called = False

    def register(**kwargs):
        nonlocal called
        called = True
        return 7, _company()

    monkeypatch.setattr(
        flow,
        "register_company_candidate",
        register,
    )

    try:
        flow.run_application_flow(
            connection=object(),
            candidate=_candidate(),
            exchange="NASDAQ",
            fundamental_profile="operating",
            price_provider=object(),
            fundamentals_provider=object(),
            estimate_provider=object(),
            dividend_provider=object(),
            initial_price_date=date(2024, 1, 1),
            end_date=date(2026, 9, 24),
            as_of_date=date(2026, 9, 25),
            scenarios=SCENARIOS,
        )
    except ValueError as exc:
        assert "as_of_date" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert called is False


def test_describe_analysis_state_without_analysis():
    result = flow.ApplicationFlowResult(
        company_id=7,
        company=_company(),
        onboarding=_onboarding(),
        coverage=_coverage(forward_eps_period=None),
        analysis=None,
        radar_input=None,
    )

    assert (
        flow.describe_analysis_state(result)
        == "insufficient"
    )
