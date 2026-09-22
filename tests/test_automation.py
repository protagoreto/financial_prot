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
