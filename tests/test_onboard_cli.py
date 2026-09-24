from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import scripts.onboard as cli
from src.db import connect, initialize_database
from src.ingestion import get_or_create_company
from src.onboarding import (
    CompanyOnboardingResult,
    OnboardingStatus,
    OnboardingStepResult,
)


def _database(tmp_path: Path) -> tuple[Path, int]:
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Test Company",
            ticker="TEST",
            exchange="NASDAQ",
            currency="USD",
            fundamental_profile="operating",
            symbol="TEST",
        )

    return db_path, company_id


def _result(company_id: int):
    return CompanyOnboardingResult(
        company_id=company_id,
        symbol="TEST",
        steps=(
            OnboardingStepResult(
                name="prices",
                status=OnboardingStatus.SUCCESS,
                processed=10,
            ),
            OnboardingStepResult(
                name="financials",
                status=OnboardingStatus.SUCCESS,
                processed=20,
            ),
            OnboardingStepResult(
                name="forward_eps",
                status=OnboardingStatus.UNAVAILABLE,
                detail="not available",
            ),
            OnboardingStepResult(
                name="dividends",
                status=OnboardingStatus.SUCCESS,
                processed=0,
            ),
        ),
    )


def test_cli_onboards_by_company_id(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    db_path, company_id = _database(tmp_path)

    calls = []

    def fake_onboard_company(**kwargs):
        calls.append(kwargs)
        return _result(company_id)

    monkeypatch.setattr(
        cli,
        "onboard_company",
        fake_onboard_company,
    )

    exit_code = cli.main(
        [
            "--company-id",
            str(company_id),
            "--initial-price-date",
            "2020-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(db_path),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["company_id"] == company_id
    assert calls[0]["initial_price_date"] == date(
        2020,
        1,
        1,
    )
    assert calls[0]["end_date"] == date(
        2026,
        9,
        24,
    )

    assert "symbol: TEST" in output
    assert "prices: success processed=10" in output
    assert "forward_eps: unavailable" in output
    assert "dividends: success processed=0" in output
    assert "success: 3" in output
    assert "unavailable: 1" in output
    assert "failed: 0" in output
    assert "point_in_time_note:" in output


def test_cli_resolves_ticker_and_exchange(
    tmp_path: Path,
    monkeypatch,
):
    db_path, company_id = _database(tmp_path)

    observed = {}

    def fake_onboard_company(**kwargs):
        observed.update(kwargs)
        return _result(company_id)

    monkeypatch.setattr(
        cli,
        "onboard_company",
        fake_onboard_company,
    )

    exit_code = cli.main(
        [
            "--ticker",
            "test",
            "--exchange",
            "nasdaq",
            "--initial-price-date",
            "2020-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(db_path),
        ]
    )

    assert exit_code == 0
    assert observed["company_id"] == company_id


def test_cli_requires_exchange_with_ticker(
    tmp_path: Path,
):
    db_path, _ = _database(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--ticker",
                "TEST",
                "--initial-price-date",
                "2020-01-01",
                "--db-path",
                str(db_path),
            ]
        )

    assert exc.value.code == 2


def test_cli_rejects_exchange_with_company_id(
    tmp_path: Path,
):
    db_path, company_id = _database(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--company-id",
                str(company_id),
                "--exchange",
                "NASDAQ",
                "--initial-price-date",
                "2020-01-01",
                "--db-path",
                str(db_path),
            ]
        )

    assert exc.value.code == 2


def test_cli_rejects_invalid_date_range(
    tmp_path: Path,
):
    db_path, company_id = _database(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--company-id",
                str(company_id),
                "--initial-price-date",
                "2026-09-25",
                "--end-date",
                "2026-09-24",
                "--db-path",
                str(db_path),
            ]
        )

    assert exc.value.code == 2


def test_cli_returns_nonzero_for_failed_step(
    tmp_path: Path,
    monkeypatch,
):
    db_path, company_id = _database(tmp_path)

    failed_result = CompanyOnboardingResult(
        company_id=company_id,
        symbol="TEST",
        steps=(
            OnboardingStepResult(
                name="prices",
                status=OnboardingStatus.FAILED,
                detail="RuntimeError: provider failure",
            ),
        ),
    )

    monkeypatch.setattr(
        cli,
        "onboard_company",
        lambda **kwargs: failed_result,
    )

    exit_code = cli.main(
        [
            "--company-id",
            str(company_id),
            "--initial-price-date",
            "2020-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(db_path),
        ]
    )

    assert exit_code == 1


def test_onboard_cli_passes_sec_publication_provider(
    tmp_path: Path,
    monkeypatch,
):
    db_path, company_id = _database(tmp_path)
    captured = {}

    class FakeSecProvider:
        def __init__(self, user_agent):
            self.user_agent = user_agent
            captured["constructed_provider"] = self
            captured["user_agent"] = user_agent

    def fake_onboard_company(**kwargs):
        captured["onboard_kwargs"] = kwargs
        return _result(company_id)

    monkeypatch.setattr(
        cli,
        "settings",
        replace(
            cli.settings,
            sec_user_agent="financial_prot test@example.com",
        ),
    )
    monkeypatch.setattr(
        cli,
        "SecPublicationDateProvider",
        FakeSecProvider,
    )
    monkeypatch.setattr(
        cli,
        "onboard_company",
        fake_onboard_company,
    )

    exit_code = cli.main(
        [
            "--company-id",
            str(company_id),
            "--initial-price-date",
            "2020-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(db_path),
        ]
    )

    assert exit_code == 0
    assert captured["user_agent"] == (
        "financial_prot test@example.com"
    )
    assert (
        captured["onboard_kwargs"]["publication_date_provider"]
        is captured["constructed_provider"]
    )


def test_onboard_cli_passes_no_publication_provider_when_unconfigured(
    tmp_path: Path,
    monkeypatch,
):
    db_path, company_id = _database(tmp_path)
    captured = {}

    class UnexpectedSecProvider:
        def __init__(self, user_agent):
            raise AssertionError(
                "SEC provider must not be constructed"
            )

    def fake_onboard_company(**kwargs):
        captured.update(kwargs)
        return _result(company_id)

    monkeypatch.setattr(
        cli,
        "settings",
        replace(
            cli.settings,
            sec_user_agent=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "SecPublicationDateProvider",
        UnexpectedSecProvider,
    )
    monkeypatch.setattr(
        cli,
        "onboard_company",
        fake_onboard_company,
    )

    exit_code = cli.main(
        [
            "--company-id",
            str(company_id),
            "--initial-price-date",
            "2020-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(db_path),
        ]
    )

    assert exit_code == 0
    assert captured["publication_date_provider"] is None
