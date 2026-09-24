from datetime import date
from pathlib import Path

import pytest

import scripts.company_flow as cli
from src.application_flow import ApplicationFlowResult
from src.coverage import CompanyCoverage
from src.investment import AnalysisAvailability
from src.onboarding import (
    CompanyOnboardingResult,
    OnboardingStatus,
    OnboardingStepResult,
)
from src.providers.discovery_base import CompanyCandidate
from src.radar import RadarCompanyInput
from src.universe import CompanyConfig


def _candidate() -> CompanyCandidate:
    return CompanyCandidate(
        symbol="TEST",
        name="Test Company",
        currency="USD",
        provider_exchange="NMS",
    )


def _coverage() -> CompanyCoverage:
    return CompanyCoverage(
        company_id=7,
        as_of_date=date(2026, 9, 24),
        price_available=True,
        fundamental_snapshot_available=False,
        fundamental_growth_available=False,
        forward_eps_period=date(2027, 6, 30),
        estimate_count=1,
        dividend_count=5,
        missing_snapshot_metrics=(),
        missing_growth_metrics=(),
    )


class PartialAnalysis:
    availability = AnalysisAvailability.VALUATION_ONLY
    valuation = object()
    fundamentals = None


def _result() -> ApplicationFlowResult:
    company = CompanyConfig(
        name="Test Company",
        ticker="TEST",
        symbol="TEST",
        exchange="NASDAQ",
        currency="USD",
        fundamental_profile="operating",
    )

    onboarding = CompanyOnboardingResult(
        company_id=7,
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
                status=OnboardingStatus.SUCCESS,
                processed=1,
            ),
            OnboardingStepResult(
                name="dividends",
                status=OnboardingStatus.SUCCESS,
                processed=5,
            ),
        ),
    )

    return ApplicationFlowResult(
        company_id=7,
        company=company,
        onboarding=onboarding,
        coverage=_coverage(),
        analysis=PartialAnalysis(),
        radar_input=RadarCompanyInput(
            company_id=7,
            fiscal_period_end=date(2027, 6, 30),
        ),
    )


def test_cli_discovery_only(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        cli,
        "discover_companies",
        lambda **kwargs: (_candidate(),),
    )

    exit_code = cli.main(["Microsoft"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "=== COMPANY DISCOVERY ===" in output
    assert "symbol=TEST" in output
    assert "name=Test Company" in output


def test_cli_selected_runs_complete_flow(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    candidate = _candidate()
    observed = {}

    monkeypatch.setattr(
        cli,
        "discover_companies",
        lambda **kwargs: (candidate,),
    )
    monkeypatch.setattr(
        cli.YahooCompanyDiscoveryProvider,
        "enrich",
        lambda self, value: value,
    )

    def fake_flow(**kwargs):
        observed.update(kwargs)
        return _result()

    monkeypatch.setattr(
        cli,
        "run_application_flow",
        fake_flow,
    )

    exit_code = cli.main(
        [
            "Microsoft",
            "--select",
            "1",
            "--exchange",
            "NASDAQ",
            "--fundamental-profile",
            "operating",
            "--initial-price-date",
            "2024-01-01",
            "--end-date",
            "2026-09-24",
            "--as-of-date",
            "2026-09-24",
            "--db-path",
            str(tmp_path / "flow.sqlite"),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert observed["candidate"] is candidate
    assert observed["exchange"] == "NASDAQ"
    assert (
        observed["initial_price_date"]
        == date(2024, 1, 1)
    )
    assert observed["as_of_date"] == date(2026, 9, 24)

    assert "=== APPLICATION FLOW ===" in output
    assert "availability: valuation_only" in output
    assert "valuation: available" in output
    assert "fundamentals: unavailable" in output
    assert "eligible: True" in output
    assert "point_in_time_note:" in output


def test_cli_requires_processing_options_with_select():
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "Microsoft",
                "--select",
                "1",
            ]
        )

    assert exc.value.code == 2


def test_cli_rejects_processing_options_without_select():
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "Microsoft",
                "--exchange",
                "NASDAQ",
            ]
        )

    assert exc.value.code == 2


def test_cli_rejects_selection_out_of_range(
    monkeypatch,
):
    monkeypatch.setattr(
        cli,
        "discover_companies",
        lambda **kwargs: (_candidate(),),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "Microsoft",
                "--select",
                "2",
                "--exchange",
                "NASDAQ",
                "--fundamental-profile",
                "operating",
                "--initial-price-date",
                "2024-01-01",
            ]
        )

    assert exc.value.code == 2


def test_cli_uses_end_date_as_default_as_of(
    tmp_path: Path,
    monkeypatch,
):
    candidate = _candidate()
    observed = {}

    monkeypatch.setattr(
        cli,
        "discover_companies",
        lambda **kwargs: (candidate,),
    )
    monkeypatch.setattr(
        cli.YahooCompanyDiscoveryProvider,
        "enrich",
        lambda self, value: value,
    )

    def fake_flow(**kwargs):
        observed.update(kwargs)
        return _result()

    monkeypatch.setattr(
        cli,
        "run_application_flow",
        fake_flow,
    )

    exit_code = cli.main(
        [
            "Microsoft",
            "--select",
            "1",
            "--exchange",
            "NASDAQ",
            "--fundamental-profile",
            "operating",
            "--initial-price-date",
            "2024-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(tmp_path / "flow.sqlite"),
        ]
    )

    assert exit_code == 0
    assert observed["as_of_date"] == date(2026, 9, 24)


def test_cli_returns_nonzero_for_failed_onboarding(
    tmp_path: Path,
    monkeypatch,
):
    candidate = _candidate()
    result = _result()

    failed = ApplicationFlowResult(
        company_id=result.company_id,
        company=result.company,
        onboarding=CompanyOnboardingResult(
            company_id=7,
            symbol="TEST",
            steps=(
                OnboardingStepResult(
                    name="prices",
                    status=OnboardingStatus.FAILED,
                    detail="RuntimeError: provider failure",
                ),
            ),
        ),
        coverage=result.coverage,
        analysis=result.analysis,
        radar_input=result.radar_input,
    )

    monkeypatch.setattr(
        cli,
        "discover_companies",
        lambda **kwargs: (candidate,),
    )
    monkeypatch.setattr(
        cli.YahooCompanyDiscoveryProvider,
        "enrich",
        lambda self, value: value,
    )
    monkeypatch.setattr(
        cli,
        "run_application_flow",
        lambda **kwargs: failed,
    )

    exit_code = cli.main(
        [
            "Microsoft",
            "--select",
            "1",
            "--exchange",
            "NASDAQ",
            "--fundamental-profile",
            "operating",
            "--initial-price-date",
            "2024-01-01",
            "--end-date",
            "2026-09-24",
            "--db-path",
            str(tmp_path / "flow.sqlite"),
        ]
    )

    assert exit_code == 1
