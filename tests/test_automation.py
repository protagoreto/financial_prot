from src.assessment import AssessmentPolicy
from src.automation import RadarRunConfig
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


def _company(
    ticker: str = "TEST",
    exchange: str = "BME",
) -> CompanyConfig:
    return CompanyConfig(
        name="Test Company",
        ticker=ticker,
        symbol=f"{ticker}.MC",
        exchange=exchange,
        currency="EUR",
    )


def _scenario(
    name: str = "Base",
) -> ValuationScenario:
    return ValuationScenario(
        name=name,
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )


def _config(
    universe: tuple[CompanyConfig, ...] | None = None,
    scenarios: tuple[ValuationScenario, ...] | None = None,
    target_return: float = 0.10,
    years: int = 5,
    assessment_policy: AssessmentPolicy = AssessmentPolicy(),
    low_net_debt_threshold: float = 2.0,
) -> RadarRunConfig:
    return RadarRunConfig(
        universe=universe or (_company(),),
        scenarios=scenarios or (_scenario(),),
        target_return=target_return,
        years=years,
        assessment_policy=assessment_policy,
        low_net_debt_threshold=low_net_debt_threshold,
    )


def test_radar_run_config_accepts_valid_configuration():
    assert _config().is_valid() is True


def test_radar_run_config_rejects_empty_universe():
    config = RadarRunConfig(
        universe=(),
        scenarios=(_scenario(),),
    )

    assert config.is_valid() is False


def test_radar_run_config_rejects_empty_scenarios():
    config = RadarRunConfig(
        universe=(_company(),),
        scenarios=(),
    )

    assert config.is_valid() is False


def test_radar_run_config_rejects_invalid_target_return():
    assert _config(target_return=-1.0).is_valid() is False


def test_radar_run_config_rejects_invalid_years():
    assert _config(years=0).is_valid() is False


def test_radar_run_config_rejects_invalid_assessment_policy():
    policy = AssessmentPolicy(
        min_quality_signals=0,
    )

    assert (
        _config(
            assessment_policy=policy,
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_negative_debt_threshold():
    assert (
        _config(
            low_net_debt_threshold=-0.1,
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_blank_company_identity():
    assert (
        _config(
            universe=(
                _company(
                    ticker=" ",
                ),
            ),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_duplicate_company_identity():
    assert (
        _config(
            universe=(
                _company(
                    ticker="TEST",
                    exchange="BME",
                ),
                _company(
                    ticker="test",
                    exchange="bme",
                ),
            ),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_blank_scenario_name():
    assert (
        _config(
            scenarios=(
                _scenario(name=" "),
            ),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_duplicate_scenario_names():
    assert (
        _config(
            scenarios=(
                _scenario(name="Base"),
                _scenario(name="base"),
            ),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_invalid_eps_growth():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=-1.0,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    assert (
        _config(
            scenarios=(scenario,),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_invalid_dividend_yield():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=-1.0,
        terminal_pe=15.0,
    )

    assert (
        _config(
            scenarios=(scenario,),
        ).is_valid()
        is False
    )


def test_radar_run_config_rejects_invalid_terminal_pe():
    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.08,
        dividend_yield=0.02,
        terminal_pe=0.0,
    )

    assert (
        _config(
            scenarios=(scenario,),
        ).is_valid()
        is False
    )


def test_audited_radar_records_exception_type_for_empty_error(
    tmp_path,
):
    from datetime import date
    import sqlite3
    from unittest.mock import patch

    import pytest

    from src.automation import (
        RadarRunConfig,
        run_audited_radar,
    )
    from src.db import initialize_database

    db_path = tmp_path / "empty-error.sqlite"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)

    try:
        config = RadarRunConfig(
            universe=(),
            scenarios=(),
        )

        with patch(
            "src.automation.run_automated_radar",
            side_effect=Exception(),
        ):
            with pytest.raises(Exception):
                run_audited_radar(
                    connection=connection,
                    config=config,
                    as_of_date=date(2026, 9, 23),
                    model_version="m14.5-test",
                    data_version="data-test",
                )

        row = connection.execute(
            """
            SELECT status, error
            FROM analysis_runs
            ORDER BY run_id DESC
            LIMIT 1
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "failed"
        assert row[1] == "Exception"
    finally:
        connection.close()
