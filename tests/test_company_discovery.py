from pathlib import Path

import pytest

from src.company_discovery import (
    build_company_config,
    discover_companies,
    register_company_candidate,
)
from src.db import connect, initialize_database
from src.providers.discovery_base import (
    CompanyCandidate,
    CompanyDiscoveryProvider,
)


class RecordingDiscoveryProvider(
    CompanyDiscoveryProvider
):
    def __init__(
        self,
        candidates: tuple[CompanyCandidate, ...],
    ) -> None:
        self.candidates = candidates
        self.calls: list[tuple[str, int]] = []

    @property
    def name(self) -> str:
        return "recording"

    def search(
        self,
        query: str,
        max_results: int = 8,
    ) -> tuple[CompanyCandidate, ...]:
        self.calls.append((query, max_results))
        return self.candidates

    def enrich(
        self,
        candidate: CompanyCandidate,
    ) -> CompanyCandidate:
        return candidate


def _candidate() -> CompanyCandidate:
    return CompanyCandidate(
        symbol="ABC.MC",
        name="Example Company",
        provider_exchange="MCE",
        exchange_display="Madrid",
        quote_type="EQUITY",
        currency="EUR",
        sector="Industrials",
        industry="Example Industry",
        country="Spain",
    )


def test_discover_companies_delegates_to_provider():
    candidate = _candidate()
    provider = RecordingDiscoveryProvider(
        (candidate,)
    )

    result = discover_companies(
        provider,
        "Example",
        max_results=5,
    )

    assert result == (candidate,)
    assert provider.calls == [("Example", 5)]


def test_build_company_config_requires_explicit_profile():
    candidate = _candidate()

    with pytest.raises(
        ValueError,
        match="fundamental_profile",
    ):
        build_company_config(
            candidate,
            exchange="BME",
            fundamental_profile="unknown",
        )


def test_build_company_config_preserves_provider_symbol():
    company = build_company_config(
        _candidate(),
        exchange="BME",
        fundamental_profile="operating",
    )

    assert company.ticker == "ABC"
    assert company.symbol == "ABC.MC"
    assert company.exchange == "BME"
    assert company.currency == "EUR"


def test_register_company_candidate_is_idempotent(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    candidate = _candidate()

    with connect(db_path) as connection:
        first_id, first = register_company_candidate(
            connection,
            candidate,
            exchange="BME",
            fundamental_profile="operating",
        )
        second_id, second = register_company_candidate(
            connection,
            candidate,
            exchange="bme",
            fundamental_profile="operating",
        )

        count = connection.execute(
            "SELECT COUNT(*) AS count FROM companies"
        ).fetchone()["count"]

    assert first_id == second_id
    assert first == second
    assert count == 1


def test_registration_requires_currency(
    tmp_path: Path,
):
    candidate = CompanyCandidate(
        symbol="ABC",
        name="Example",
    )

    with pytest.raises(
        ValueError,
        match="currency",
    ):
        build_company_config(
            candidate,
            exchange="TEST",
            fundamental_profile="operating",
        )
