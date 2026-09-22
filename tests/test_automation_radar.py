from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from src.assessment import AssessmentPolicy
from src.automation import (
    RadarRunConfig,
    run_audited_radar,
    run_automated_radar,
)
from src.db import connect, initialize_database
from src.radar import RadarSnapshot
from src.radar_service import RadarRun
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig
from src.radar_universe import (
    RadarUniverseIssue,
    RadarUniverseUnresolved,
)

AS_OF_DATE = date(2026, 9, 22)


def _company() -> CompanyConfig:
    return CompanyConfig(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
        exchange="BME",
        currency="EUR",
    )


def _scenario() -> ValuationScenario:
    return ValuationScenario(
        name="Base",
        eps_growth=0.05,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )


def _config() -> RadarRunConfig:
    return RadarRunConfig(
        universe=(_company(),),
        scenarios=(_scenario(),),
    )


def _radar_run(
    unresolved=(),
) -> RadarRun:
    return RadarRun(
        snapshot=RadarSnapshot(
            as_of_date=AS_OF_DATE,
            target_return=0.10,
            years=5,
            entries=(),
        ),
        unresolved=unresolved,
    )


def test_run_automated_radar_delegates_complete_config():
    company = _company()
    scenario = _scenario()

    policy = AssessmentPolicy(
        min_quality_signals=2,
        max_risk_signals_for_low=0,
        min_risk_signals_for_high=2,
        min_value_trap_warnings=1,
    )

    config = RadarRunConfig(
        universe=(company,),
        scenarios=(scenario,),
        target_return=0.12,
        years=7,
        assessment_policy=policy,
        low_net_debt_threshold=1.5,
    )

    radar_run = RadarRun(
        snapshot=RadarSnapshot(
            as_of_date=AS_OF_DATE,
            target_return=0.12,
            years=7,
            entries=(),
        ),
        unresolved=(),
    )

    with patch(
        "src.automation.run_radar",
        return_value=radar_run,
    ) as run_mock:
        result = run_automated_radar(
            connection=None,
            config=config,
            as_of_date=AS_OF_DATE,
        )

    assert result is radar_run

    run_mock.assert_called_once_with(
        connection=None,
        universe=(company,),
        as_of_date=AS_OF_DATE,
        scenarios=(scenario,),
        target_return=0.12,
        years=7,
        assessment_policy=policy,
        low_net_debt_threshold=1.5,
    )


def test_run_automated_radar_rejects_invalid_config():
    config = RadarRunConfig(
        universe=(),
        scenarios=(_scenario(),),
    )

    with patch(
        "src.automation.run_radar"
    ) as run_mock:
        with pytest.raises(
            ValueError,
            match="^Invalid radar run configuration\\.$",
        ):
            run_automated_radar(
                connection=None,
                config=config,
                as_of_date=AS_OF_DATE,
            )

    run_mock.assert_not_called()


def test_run_automated_radar_keeps_as_of_date_external():
    config = _config()

    radar_run = _radar_run()

    with patch(
        "src.automation.run_radar",
        return_value=radar_run,
    ) as run_mock:
        run_automated_radar(
            connection=None,
            config=config,
            as_of_date=AS_OF_DATE,
        )

    assert (
        run_mock.call_args.kwargs["as_of_date"]
        == AS_OF_DATE
    )


def test_run_audited_radar_persists_success(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    radar_run = _radar_run()

    with connect(db_path) as connection:
        with patch(
            "src.automation.run_automated_radar",
            return_value=radar_run,
        ):
            result = run_audited_radar(
                connection=connection,
                config=_config(),
                as_of_date=AS_OF_DATE,
                model_version="m9.5-test",
                data_version="data-test",
            )

        row = connection.execute(
            """
            SELECT *
            FROM analysis_runs
            """
        ).fetchone()

    assert result is radar_run
    assert row["status"] == "success"
    assert row["model_version"] == "m9.5-test"
    assert row["data_version"] == "data-test"
    assert row["company_id"] is None
    assert row["execution_time"] >= 0
    assert row["error"] is None


def test_run_audited_radar_persists_failure_and_reraises(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with patch(
            "src.automation.run_automated_radar",
            side_effect=RuntimeError("Radar failed."),
        ):
            with pytest.raises(
                RuntimeError,
                match="^Radar failed\\.$",
            ):
                run_audited_radar(
                    connection=connection,
                    config=_config(),
                    as_of_date=AS_OF_DATE,
                    model_version="m9.5-test",
                    data_version="data-test",
                )

        row = connection.execute(
            """
            SELECT *
            FROM analysis_runs
            """
        ).fetchone()

    assert row["status"] == "failed"
    assert row["model_version"] == "m9.5-test"
    assert row["data_version"] == "data-test"
    assert row["execution_time"] >= 0
    assert row["error"] == "Radar failed."


def test_run_audited_radar_treats_unresolved_as_success(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    company = _company()

    radar_run = _radar_run(
        unresolved=(
            RadarUniverseUnresolved(
                company=company,
                issue=(
                    RadarUniverseIssue
                    .FORWARD_EPS_PERIOD_NOT_FOUND
                ),
            ),
        ),
    )

    with connect(db_path) as connection:
        with patch(
            "src.automation.run_automated_radar",
            return_value=radar_run,
        ):
            result = run_audited_radar(
                connection=connection,
                config=_config(),
                as_of_date=AS_OF_DATE,
                model_version="m9.5-test",
                data_version="data-test",
            )

        row = connection.execute(
            """
            SELECT status, error
            FROM analysis_runs
            """
        ).fetchone()

    assert result.unresolved == radar_run.unresolved
    assert row["status"] == "success"
    assert row["error"] is None


def test_run_audited_radar_appends_audit_record_per_execution(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    radar_run = _radar_run()

    with connect(db_path) as connection:
        with patch(
            "src.automation.run_automated_radar",
            return_value=radar_run,
        ):
            for _ in range(2):
                run_audited_radar(
                    connection=connection,
                    config=_config(),
                    as_of_date=AS_OF_DATE,
                    model_version="m9.5-test",
                    data_version="data-test",
                )

        run_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM analysis_runs
            """
        ).fetchone()["count"]

    assert run_count == 2
