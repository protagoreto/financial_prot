from datetime import date
from unittest.mock import patch

from src.radar import (
    RadarCompanyInput,
    RadarSnapshot,
)
from src.radar_service import run_radar
from src.radar_universe import (
    RadarUniverseIssue,
    RadarUniverseResolution,
    RadarUniverseUnresolved,
)
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


AS_OF_DATE = date(2026, 9, 22)


def _company(
    ticker: str = "TEST",
) -> CompanyConfig:
    return CompanyConfig(
        name=f"{ticker} Company",
        ticker=ticker,
        symbol=f"{ticker}.MC",
        exchange="BME",
        currency="EUR",
    )


def _scenario() -> ValuationScenario:
    return ValuationScenario(
        name="base",
        eps_growth=0.05,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )


def test_run_radar_resolves_universe_and_builds_snapshot():
    company = _company()

    radar_input = RadarCompanyInput(
        company_id=1,
        fiscal_period_end=date(2026, 12, 31),
    )

    resolution = RadarUniverseResolution(
        inputs=(radar_input,),
        unresolved=(),
    )

    snapshot = RadarSnapshot(
        as_of_date=AS_OF_DATE,
        target_return=0.10,
        years=5,
        entries=(),
    )

    with (
        patch(
            "src.radar_service.resolve_radar_universe",
            return_value=resolution,
        ) as resolve_mock,
        patch(
            "src.radar_service.build_radar_snapshot",
            return_value=snapshot,
        ) as build_mock,
    ):
        result = run_radar(
            connection=None,
            universe=(company,),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    assert result.snapshot is snapshot
    assert result.unresolved == ()

    resolve_mock.assert_called_once_with(
        connection=None,
        universe=(company,),
        as_of_date=AS_OF_DATE,
    )

    build_mock.assert_called_once_with(
        connection=None,
        companies=(radar_input,),
        as_of_date=AS_OF_DATE,
        scenarios=(_scenario(),),
        target_return=0.10,
        years=5,
        assessment_policy=build_mock.call_args.kwargs[
            "assessment_policy"
        ],
        low_net_debt_threshold=2.0,
    )


def test_run_radar_preserves_unresolved_companies():
    company = _company()

    unresolved = RadarUniverseUnresolved(
        company=company,
        issue=RadarUniverseIssue.COMPANY_NOT_FOUND,
    )

    resolution = RadarUniverseResolution(
        inputs=(),
        unresolved=(unresolved,),
    )

    snapshot = RadarSnapshot(
        as_of_date=AS_OF_DATE,
        target_return=0.10,
        years=5,
        entries=(),
    )

    with (
        patch(
            "src.radar_service.resolve_radar_universe",
            return_value=resolution,
        ),
        patch(
            "src.radar_service.build_radar_snapshot",
            return_value=snapshot,
        ) as build_mock,
    ):
        result = run_radar(
            connection=None,
            universe=(company,),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    assert result.snapshot is snapshot
    assert result.unresolved == (unresolved,)

    assert (
        build_mock.call_args.kwargs["companies"]
        == ()
    )


def test_run_radar_propagates_configuration():
    scenario = _scenario()

    resolution = RadarUniverseResolution(
        inputs=(),
        unresolved=(),
    )

    snapshot = RadarSnapshot(
        as_of_date=AS_OF_DATE,
        target_return=0.12,
        years=7,
        entries=(),
    )

    with (
        patch(
            "src.radar_service.resolve_radar_universe",
            return_value=resolution,
        ),
        patch(
            "src.radar_service.build_radar_snapshot",
            return_value=snapshot,
        ) as build_mock,
    ):
        result = run_radar(
            connection=None,
            universe=(),
            as_of_date=AS_OF_DATE,
            scenarios=(scenario,),
            target_return=0.12,
            years=7,
            low_net_debt_threshold=1.5,
        )

    assert result.snapshot is snapshot

    assert build_mock.call_args.kwargs[
        "target_return"
    ] == 0.12
    assert build_mock.call_args.kwargs["years"] == 7
    assert (
        build_mock.call_args.kwargs[
            "low_net_debt_threshold"
        ]
        == 1.5
    )


def test_run_radar_passes_resolved_inputs_only():
    first = RadarCompanyInput(
        company_id=10,
        fiscal_period_end=date(2026, 12, 31),
    )
    second = RadarCompanyInput(
        company_id=20,
        fiscal_period_end=date(2027, 3, 31),
    )

    resolution = RadarUniverseResolution(
        inputs=(first, second),
        unresolved=(),
    )

    snapshot = RadarSnapshot(
        as_of_date=AS_OF_DATE,
        target_return=0.10,
        years=5,
        entries=(),
    )

    with (
        patch(
            "src.radar_service.resolve_radar_universe",
            return_value=resolution,
        ),
        patch(
            "src.radar_service.build_radar_snapshot",
            return_value=snapshot,
        ) as build_mock,
    ):
        run_radar(
            connection=None,
            universe=(),
            as_of_date=AS_OF_DATE,
            scenarios=(_scenario(),),
        )

    assert (
        build_mock.call_args.kwargs["companies"]
        == (first, second)
    )
