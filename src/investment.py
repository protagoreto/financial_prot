from dataclasses import dataclass
from datetime import date
from enum import Enum
import sqlite3

from src.analysis import (
    ValuationAnalysis,
    build_valuation_analysis,
)
from src.assessment import (
    AssessmentPolicy,
    FundamentalAssessment,
    assess_fundamentals,
)
from src.financial_assessment import (
    assess_financial_fundamentals,
)
from src.financial_signals import (
    build_financial_fundamental_signals,
)
from src.repository import get_company_by_id
from src.scenarios import ValuationScenario
from src.signals import build_fundamental_signals
from src.value import ValueAssessment, assess_value


class AnalysisAvailability(str, Enum):
    COMPLETE = "complete"
    VALUATION_ONLY = "valuation_only"
    FUNDAMENTALS_ONLY = "fundamentals_only"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class InvestmentAnalysis:
    company_id: int
    as_of_date: date

    availability: AnalysisAvailability

    valuation: ValuationAnalysis | None
    value: ValueAssessment | None
    fundamentals: FundamentalAssessment | None


def build_investment_analysis(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
    fiscal_period_end: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float = 0.10,
    years: int = 5,
    assessment_policy: AssessmentPolicy = AssessmentPolicy(),
    low_net_debt_threshold: float = 2.0,
) -> InvestmentAnalysis:
    valuation = build_valuation_analysis(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
        fiscal_period_end=fiscal_period_end,
        scenarios=scenarios,
        target_return=target_return,
        years=years,
    )

    value = (
        assess_value(valuation)
        if valuation is not None
        else None
    )

    company = get_company_by_id(
        connection=connection,
        company_id=company_id,
    )

    fundamentals = None

    if (
        company is not None
        and company.fundamental_profile.value == "financial"
    ):
        financial_signals = (
            build_financial_fundamental_signals(
                connection=connection,
                company_id=company_id,
                as_of_date=as_of_date,
            )
        )

        if financial_signals is not None:
            fundamentals = assess_financial_fundamentals(
                signals=financial_signals,
                policy=assessment_policy,
            )
    else:
        signals = build_fundamental_signals(
            connection=connection,
            company_id=company_id,
            as_of_date=as_of_date,
            low_net_debt_threshold=low_net_debt_threshold,
        )

        if signals is not None:
            fundamentals = assess_fundamentals(
                signals=signals,
                policy=assessment_policy,
            )

    availability = _determine_availability(
        valuation=valuation,
        fundamentals=fundamentals,
    )

    return InvestmentAnalysis(
        company_id=company_id,
        as_of_date=as_of_date,
        availability=availability,
        valuation=valuation,
        value=value,
        fundamentals=fundamentals,
    )


def _determine_availability(
    valuation: ValuationAnalysis | None,
    fundamentals: FundamentalAssessment | None,
) -> AnalysisAvailability:
    if (
        valuation is not None
        and fundamentals is not None
    ):
        return AnalysisAvailability.COMPLETE

    if valuation is not None:
        return AnalysisAvailability.VALUATION_ONLY

    if fundamentals is not None:
        return AnalysisAvailability.FUNDAMENTALS_ONLY

    return AnalysisAvailability.INSUFFICIENT
