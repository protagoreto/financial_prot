from dataclasses import dataclass
from datetime import date
import sqlite3

from src.company_discovery import register_company_candidate
from src.coverage import CompanyCoverage, build_company_coverage
from src.investment import (
    AnalysisAvailability,
    InvestmentAnalysis,
    build_investment_analysis,
)
from src.onboarding import (
    CompanyOnboardingResult,
    onboard_company,
)
from src.providers.discovery_base import CompanyCandidate
from src.radar import RadarCompanyInput
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


@dataclass(frozen=True)
class ApplicationFlowResult:
    company_id: int
    company: CompanyConfig
    onboarding: CompanyOnboardingResult
    coverage: CompanyCoverage
    analysis: InvestmentAnalysis | None
    radar_input: RadarCompanyInput | None

    @property
    def analysis_available(self) -> bool:
        return self.analysis is not None

    @property
    def radar_eligible(self) -> bool:
        return self.radar_input is not None


def run_application_flow(
    connection: sqlite3.Connection,
    candidate: CompanyCandidate,
    exchange: str,
    fundamental_profile: str,
    price_provider,
    fundamentals_provider,
    estimate_provider,
    dividend_provider,
    initial_price_date: date,
    end_date: date,
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    estimate_date: date | None = None,
    target_return: float = 0.10,
    years: int = 5,
    publication_date_provider=None,
) -> ApplicationFlowResult:
    if initial_price_date > end_date:
        raise ValueError(
            "initial_price_date cannot be after end_date"
        )

    if as_of_date > end_date:
        raise ValueError(
            "as_of_date cannot be after end_date"
        )

    if target_return <= -1.0:
        raise ValueError(
            "target_return must be greater than -1."
        )

    if years <= 0:
        raise ValueError(
            "years must be greater than zero."
        )

    if not scenarios:
        raise ValueError(
            "At least one scenario is required."
        )

    company_id, company = register_company_candidate(
        connection=connection,
        candidate=candidate,
        exchange=exchange,
        fundamental_profile=fundamental_profile,
    )

    onboarding = onboard_company(
        connection=connection,
        company_id=company_id,
        price_provider=price_provider,
        fundamentals_provider=fundamentals_provider,
        estimate_provider=estimate_provider,
        dividend_provider=dividend_provider,
        initial_price_date=initial_price_date,
        end_date=end_date,
        estimate_date=estimate_date,
        publication_date_provider=publication_date_provider,
    )

    coverage = build_company_coverage(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    analysis = _build_analysis_if_possible(
        connection=connection,
        company_id=company_id,
        coverage=coverage,
        as_of_date=as_of_date,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
    )

    radar_input = _build_radar_input(
        company_id=company_id,
        coverage=coverage,
    )

    return ApplicationFlowResult(
        company_id=company_id,
        company=company,
        onboarding=onboarding,
        coverage=coverage,
        analysis=analysis,
        radar_input=radar_input,
    )


def _build_analysis_if_possible(
    connection: sqlite3.Connection,
    company_id: int,
    coverage: CompanyCoverage,
    as_of_date: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float,
    years: int,
) -> InvestmentAnalysis | None:
    fiscal_period_end = coverage.forward_eps_period

    if fiscal_period_end is None:
        return None

    return build_investment_analysis(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
        fiscal_period_end=fiscal_period_end,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
    )


def _build_radar_input(
    company_id: int,
    coverage: CompanyCoverage,
) -> RadarCompanyInput | None:
    if coverage.forward_eps_period is None:
        return None

    return RadarCompanyInput(
        company_id=company_id,
        fiscal_period_end=coverage.forward_eps_period,
    )


def describe_analysis_state(
    result: ApplicationFlowResult,
) -> str:
    if result.analysis is None:
        return AnalysisAvailability.INSUFFICIENT.value

    return result.analysis.availability.value
