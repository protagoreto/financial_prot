from dataclasses import dataclass
from datetime import date
import sqlite3

from src.scenarios import (
    ScenarioResult,
    ValuationScenario,
    evaluate_scenarios,
)
from src.valuation import (
    ForwardValuationSnapshot,
    build_forward_valuation_snapshot,
)


@dataclass(frozen=True)
class ValuationAnalysis:
    company_id: int
    as_of_date: date
    target_return: float
    years: int

    snapshot: ForwardValuationSnapshot
    scenarios: tuple[ScenarioResult, ...]


def build_valuation_analysis(
    connection: sqlite3.Connection,
    company_id: int,
    as_of_date: date,
    fiscal_period_end: date,
    scenarios: tuple[ValuationScenario, ...],
    target_return: float = 0.10,
    years: int = 5,
) -> ValuationAnalysis | None:
    snapshot = build_forward_valuation_snapshot(
        connection=connection,
        company_id=company_id,
        as_of_date=as_of_date,
        fiscal_period_end=fiscal_period_end,
    )

    if snapshot is None:
        return None

    if snapshot.forward_pe is None:
        return None

    results = evaluate_scenarios(
        scenarios=scenarios,
        current_pe=snapshot.forward_pe,
        forward_eps=snapshot.forward_eps,
        target_return=target_return,
        years=years,
    )

    return ValuationAnalysis(
        company_id=company_id,
        as_of_date=as_of_date,
        target_return=target_return,
        years=years,
        snapshot=snapshot,
        scenarios=results,
    )