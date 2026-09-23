from dataclasses import dataclass
from datetime import date
import sqlite3
from time import perf_counter


from src.assessment import AssessmentPolicy
from src.ingestion import (
    get_or_create_company,
    ingest_prices_incremental,
)
from src.models import (
    AnalysisRunRecord,
    AnalysisRunStatus,
)
from src.providers.base import PriceProvider
from src.radar_service import RadarRun, run_radar
from src.repository import insert_analysis_run
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


@dataclass(frozen=True)
class RadarRunConfig:
    universe: tuple[CompanyConfig, ...]
    scenarios: tuple[ValuationScenario, ...]
    target_return: float = 0.10
    years: int = 5
    assessment_policy: AssessmentPolicy = AssessmentPolicy()
    low_net_debt_threshold: float = 2.0

    def is_valid(self) -> bool:
        if not self.universe:
            return False

        if not self.scenarios:
            return False

        if self.target_return <= -1:
            return False

        if self.years <= 0:
            return False

        if not self.assessment_policy.is_valid():
            return False

        if self.low_net_debt_threshold < 0:
            return False

        if not self._has_valid_universe():
            return False

        if not self._has_valid_scenarios():
            return False

        return True

    def _has_valid_universe(self) -> bool:
        identities: set[tuple[str, str]] = set()

        for company in self.universe:
            ticker = company.ticker.strip()
            exchange = company.exchange.strip()

            if not ticker or not exchange:
                return False

            identity = (
                ticker.casefold(),
                exchange.casefold(),
            )

            if identity in identities:
                return False

            identities.add(identity)

        return True

    def _has_valid_scenarios(self) -> bool:
        names: set[str] = set()

        for scenario in self.scenarios:
            name = scenario.name.strip()

            if not name:
                return False

            normalized_name = name.casefold()

            if normalized_name in names:
                return False

            names.add(normalized_name)

            if scenario.eps_growth <= -1:
                return False

            if scenario.dividend_yield <= -1:
                return False

            if scenario.terminal_pe <= 0:
                return False

        return True


class CompanyPriceUpdateStatus(str):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class CompanyPriceUpdate:
    company: CompanyConfig
    company_id: int
    processed_records: int
    status: str = CompanyPriceUpdateStatus.SUCCESS
    error: str | None = None


@dataclass(frozen=True)
class PriceUpdateRun:
    start_date: date
    end_date: date
    companies: tuple[CompanyPriceUpdate, ...]

    @property
    def processed_records(self) -> int:
        return sum(
            company.processed_records
            for company in self.companies
        )

    @property
    def failed_companies(self) -> tuple[CompanyPriceUpdate, ...]:
        return tuple(
            company
            for company in self.companies
            if company.status == CompanyPriceUpdateStatus.FAILED
        )

    @property
    def is_complete(self) -> bool:
        return not self.failed_companies


def update_prices(
    connection: sqlite3.Connection,
    provider: PriceProvider,
    universe: tuple[CompanyConfig, ...],
    initial_start_date: date,
    end_date: date,
) -> PriceUpdateRun:
    if initial_start_date > end_date:
        raise ValueError(
            "Initial start date cannot be after end date."
        )

    updates: list[CompanyPriceUpdate] = []

    for company in universe:
        company_id = get_or_create_company(
            connection=connection,
            name=company.name,
            ticker=company.ticker,
            exchange=company.exchange,
            currency=company.currency,
        )

        try:
            processed_records = ingest_prices_incremental(
                connection=connection,
                provider=provider,
                company_id=company_id,
                symbol=company.symbol,
                currency=company.currency,
                initial_start_date=initial_start_date,
                end_date=end_date,
            )
        except Exception as exc:
            updates.append(
                CompanyPriceUpdate(
                    company=company,
                    company_id=company_id,
                    processed_records=0,
                    status=CompanyPriceUpdateStatus.FAILED,
                    error=str(exc),
                )
            )
            continue

        updates.append(
            CompanyPriceUpdate(
                company=company,
                company_id=company_id,
                processed_records=processed_records,
            )
        )

    return PriceUpdateRun(
        start_date=initial_start_date,
        end_date=end_date,
        companies=tuple(updates),
    )


def run_automated_radar(
    connection: sqlite3.Connection,
    config: RadarRunConfig,
    as_of_date: date,
) -> RadarRun:
    if not config.is_valid():
        raise ValueError("Invalid radar run configuration.")

    return run_radar(
        connection=connection,
        universe=config.universe,
        as_of_date=as_of_date,
        scenarios=config.scenarios,
        target_return=config.target_return,
        years=config.years,
        assessment_policy=config.assessment_policy,
        low_net_debt_threshold=config.low_net_debt_threshold,
    )


def run_audited_radar(
    connection: sqlite3.Connection,
    config: RadarRunConfig,
    as_of_date: date,
    model_version: str,
    data_version: str,
) -> RadarRun:
    started_at = perf_counter()

    try:
        result = run_automated_radar(
            connection=connection,
            config=config,
            as_of_date=as_of_date,
        )
    except Exception as exc:
        execution_time = perf_counter() - started_at

        insert_analysis_run(
            connection=connection,
            record=AnalysisRunRecord(
                model_version=model_version,
                data_version=data_version,
                status=AnalysisRunStatus.FAILED,
                execution_time=execution_time,
                error=(
                    str(exc).strip()
                    or type(exc).__name__
                ),
            ),
        )

        raise

    execution_time = perf_counter() - started_at

    insert_analysis_run(
        connection=connection,
        record=AnalysisRunRecord(
            model_version=model_version,
            data_version=data_version,
            status=AnalysisRunStatus.SUCCESS,
            execution_time=execution_time,
        ),
    )

    return result
