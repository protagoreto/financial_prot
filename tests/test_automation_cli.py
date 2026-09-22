from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.automation import (
    _parse_date,
    _parse_scenario,
    main,
)
from src.automation import (
    CompanyPriceUpdate,
    CompanyPriceUpdateStatus,
    PriceUpdateRun,
)
from src.radar import RadarSnapshot
from src.radar_service import RadarRun
from src.universe import IBEX_UNIVERSE


def test_parse_date_accepts_iso_date():
    assert _parse_date("2026-09-22") == date(
        2026,
        9,
        22,
    )


def test_parse_date_rejects_invalid_date():
    with pytest.raises(
        Exception,
        match="Invalid ISO date",
    ):
        _parse_date("22-09-2026")


def test_parse_scenario_builds_explicit_scenario():
    scenario = _parse_scenario(
        [
            "Base",
            "0.05",
            "0.02",
            "15.0",
        ]
    )

    assert scenario.name == "Base"
    assert scenario.eps_growth == 0.05
    assert scenario.dividend_yield == 0.02
    assert scenario.terminal_pe == 15.0


def test_prices_command_returns_zero_when_complete(
    tmp_path: Path,
):
    company = IBEX_UNIVERSE[0]

    result = PriceUpdateRun(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 22),
        companies=(
            CompanyPriceUpdate(
                company=company,
                company_id=1,
                processed_records=10,
            ),
        ),
    )

    with patch(
        "scripts.automation.initialize_database"
    ), patch(
        "scripts.automation.connect"
    ) as connect_mock, patch(
        "scripts.automation.update_prices",
        return_value=result,
    ) as update_mock:
        connection = (
            connect_mock.return_value
            .__enter__.return_value
        )

        exit_code = main(
            [
                "--db-path",
                str(tmp_path / "test.sqlite"),
                "prices",
                "--start-date",
                "2026-09-01",
                "--end-date",
                "2026-09-22",
            ]
        )

    assert exit_code == 0

    update_mock.assert_called_once()

    assert (
        update_mock.call_args.kwargs["connection"]
        is connection
    )
    assert (
        update_mock.call_args.kwargs["universe"]
        == IBEX_UNIVERSE
    )


def test_prices_command_returns_nonzero_for_partial_failure(
    tmp_path: Path,
):
    company = IBEX_UNIVERSE[0]

    result = PriceUpdateRun(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 22),
        companies=(
            CompanyPriceUpdate(
                company=company,
                company_id=1,
                processed_records=0,
                status=CompanyPriceUpdateStatus.FAILED,
                error="Provider failed.",
            ),
        ),
    )

    with patch(
        "scripts.automation.initialize_database"
    ), patch(
        "scripts.automation.connect"
    ), patch(
        "scripts.automation.update_prices",
        return_value=result,
    ):
        exit_code = main(
            [
                "--db-path",
                str(tmp_path / "test.sqlite"),
                "prices",
                "--start-date",
                "2026-09-01",
                "--end-date",
                "2026-09-22",
            ]
        )

    assert exit_code == 1


def test_radar_command_passes_explicit_scenarios(
    tmp_path: Path,
):
    radar_run = RadarRun(
        snapshot=RadarSnapshot(
            as_of_date=date(2026, 9, 22),
            target_return=0.12,
            years=7,
            entries=(),
        ),
        unresolved=(),
    )

    with patch(
        "scripts.automation.initialize_database"
    ), patch(
        "scripts.automation.connect"
    ) as connect_mock, patch(
        "scripts.automation.run_audited_radar",
        return_value=radar_run,
    ) as radar_mock:
        connection = (
            connect_mock.return_value
            .__enter__.return_value
        )

        exit_code = main(
            [
                "--db-path",
                str(tmp_path / "test.sqlite"),
                "radar",
                "--as-of-date",
                "2026-09-22",
                "--model-version",
                "model-test",
                "--data-version",
                "data-test",
                "--scenario",
                "Base",
                "0.05",
                "0.02",
                "15.0",
                "--scenario",
                "Stress",
                "-0.02",
                "0.01",
                "10.0",
                "--target-return",
                "0.12",
                "--years",
                "7",
                "--low-net-debt-threshold",
                "1.5",
            ]
        )

    assert exit_code == 0

    kwargs = radar_mock.call_args.kwargs

    assert kwargs["connection"] is connection
    assert kwargs["as_of_date"] == date(
        2026,
        9,
        22,
    )
    assert kwargs["model_version"] == "model-test"
    assert kwargs["data_version"] == "data-test"

    config = kwargs["config"]

    assert config.universe == IBEX_UNIVERSE
    assert config.target_return == 0.12
    assert config.years == 7
    assert config.low_net_debt_threshold == 1.5

    assert tuple(
        scenario.name
        for scenario in config.scenarios
    ) == (
        "Base",
        "Stress",
    )

    assert config.scenarios[0].eps_growth == 0.05
    assert config.scenarios[1].eps_growth == -0.02


def test_radar_command_requires_scenario():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "radar",
                "--as-of-date",
                "2026-09-22",
                "--model-version",
                "model-test",
                "--data-version",
                "data-test",
            ]
        )

    assert exc.value.code == 2
