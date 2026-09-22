from datetime import date
from unittest.mock import patch

import pytest

from src.assessment import AssessmentPolicy
from src.automation import (
    RadarRunConfig,
    run_automated_radar,
)
from src.radar import RadarSnapshot
from src.radar_service import RadarRun
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


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
    config = RadarRunConfig(
        universe=(_company(),),
        scenarios=(_scenario(),),
    )

    radar_run = RadarRun(
        snapshot=RadarSnapshot(
            as_of_date=AS_OF_DATE,
            target_return=0.10,
            years=5,
            entries=(),
        ),
        unresolved=(),
    )

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
