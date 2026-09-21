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
from src.scenarios import ValuationScenario
from src.signals import build_fundamental_signals


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

    signals = build_fundamental_signals(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
        low_net_debt_threshold=low_net_debt_threshold,
    )

    fundamentals = None

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