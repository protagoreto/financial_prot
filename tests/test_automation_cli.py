from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.automation import (
    _parse_date,
    _parse_scenario,
    main,
)
from src.assessment import AssessmentLevel, RiskLevel
from src.automation import (
    CompanyPriceUpdate,
    CompanyPriceUpdateStatus,
    PriceUpdateRun,
)
from src.investment import AnalysisAvailability
from src.message_runtime import MessageRuntime
from src.messaging import OutboundMessage
from src.providers.message_base import MessageProvider
from src.radar import (
    RadarEntry,
    RadarScenario,
    RadarSnapshot,
)
from src.radar_service import RadarRun
from src.universe import IBEX_UNIVERSE
from src.value import ValueCondition


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


def test_radar_command_rejects_invalid_scenario():
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
                "--scenario",
                "Base",
                "not-a-number",
                "0.02",
                "15.0",
            ]
        )

    assert exc.value.code == 2


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


class FakeMessageProvider(MessageProvider):
    def __init__(self) -> None:
        self.messages: list[OutboundMessage] = []

    @property
    def name(self) -> str:
        return "fake"

    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        self.messages.append(message)


def _notification_radar_run() -> RadarRun:
    entry = RadarEntry(
        company_id=1,
        name="Example Company",
        ticker="EX",
        exchange="TEST",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            RadarScenario(
                name="Base",
                expected_return=0.12,
                required_price=100.0,
                price_margin=0.05,
                condition=ValueCondition.TARGET_MET,
            ),
        ),
    )

    return RadarRun(
        snapshot=RadarSnapshot(
            as_of_date=date(2026, 9, 22),
            target_return=0.10,
            years=5,
            entries=(entry,),
        ),
        unresolved=(),
    )


def test_radar_command_sends_requested_notification(
    tmp_path: Path,
):
    provider = FakeMessageProvider()

    runtime = MessageRuntime(
        provider=provider,
        destination="123456",
    )

    with patch(
        "scripts.automation.initialize_database"
    ), patch(
        "scripts.automation.connect"
    ), patch(
        "scripts.automation.run_audited_radar",
        return_value=_notification_radar_run(),
    ), patch(
        "scripts.automation.get_message_runtime",
        return_value=runtime,
    ) as runtime_mock:
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
                "--notify",
                "telegram",
                "--notify-scenario",
                "Base",
            ]
        )

    assert exit_code == 0

    runtime_mock.assert_called_once_with(
        provider_name="telegram",
    )

    assert len(provider.messages) == 1

    message = provider.messages[0]

    assert message.destination == "123456"
    assert "Example Company" in message.text
    assert "Base" in message.text
    assert "0.12" in message.text


def test_radar_command_without_notify_does_not_use_runtime(
    tmp_path: Path,
):
    with patch(
        "scripts.automation.initialize_database"
    ), patch(
        "scripts.automation.connect"
    ), patch(
        "scripts.automation.run_audited_radar",
        return_value=_notification_radar_run(),
    ), patch(
        "scripts.automation.get_message_runtime"
    ) as runtime_mock:
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
            ]
        )

    assert exit_code == 0
    runtime_mock.assert_not_called()


def test_radar_notification_requires_notify_scenario(
    tmp_path: Path,
):
    with patch(
        "scripts.automation.initialize_database"
    ) as initialize_mock, patch(
        "scripts.automation.run_audited_radar"
    ) as radar_mock:
        with pytest.raises(SystemExit) as exc:
            main(
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
                    "--notify",
                    "telegram",
                ]
            )

    assert exc.value.code == 2
    initialize_mock.assert_not_called()
    radar_mock.assert_not_called()
