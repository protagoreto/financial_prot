from datetime import date

from src.dashboard import DashboardRadarResult
from src.radar_presentation import RadarPresentation
from src.radar_universe import (
    RadarUniverseIssue,
    RadarUniverseUnresolved,
)
from src.universe import CompanyConfig
from streamlit_app import (
    build_publication_date_provider,
    candidate_label,
    render_company_candidate,
    render_coverage,
    render_radar,
    render_unresolved,
)


def _empty_presentation() -> RadarPresentation:
    return RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(),
    )


def test_render_radar_handles_empty_presentation(
    monkeypatch,
):
    messages = []
    dataframes = []

    monkeypatch.setattr(
        "streamlit_app.st.title",
        lambda value: None,
    )
    monkeypatch.setattr(
        "streamlit_app.st.caption",
        lambda value: None,
    )
    monkeypatch.setattr(
        "streamlit_app.st.subheader",
        lambda value: None,
    )
    monkeypatch.setattr(
        "streamlit_app.st.info",
        messages.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.dataframe",
        lambda *args, **kwargs: dataframes.append(args),
    )

    class MetricColumn:
        def metric(self, *args, **kwargs):
            return None

    monkeypatch.setattr(
        "streamlit_app.st.columns",
        lambda count: tuple(
            MetricColumn()
            for _ in range(count)
        ),
    )

    render_radar(
        _empty_presentation()
    )

    assert len(messages) == 1
    assert dataframes == []


def test_render_unresolved_displays_domain_issue(
    monkeypatch,
):
    company = CompanyConfig(
        name="Example Company",
        ticker="EX",
        symbol="EX",
        exchange="TEST",
        currency="EUR",
    )

    result = DashboardRadarResult(
        presentation=_empty_presentation(),
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

    tables = []

    monkeypatch.setattr(
        "streamlit_app.st.subheader",
        lambda value: None,
    )
    monkeypatch.setattr(
        "streamlit_app.st.caption",
        lambda value: None,
    )
    monkeypatch.setattr(
        "streamlit_app.st.dataframe",
        lambda rows, **kwargs: tables.append(rows),
    )

    render_unresolved(result)

    assert tables == [
        [
            {
                "Empresa": "Example Company",
                "Ticker": "EX",
                "Mercado": "TEST",
                "Incidencia": (
                    "No se encontr\u00f3 el periodo de BPA estimado"
                ),
            }
        ]
    ]


def test_render_unresolved_skips_empty_input(
    monkeypatch,
):
    result = DashboardRadarResult(
        presentation=_empty_presentation(),
        unresolved=(),
    )

    subheaders = []
    tables = []

    monkeypatch.setattr(
        "streamlit_app.st.subheader",
        subheaders.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.dataframe",
        lambda *args, **kwargs: tables.append(args),
    )

    render_unresolved(result)

    assert subheaders == []
    assert tables == []

def test_candidate_label_uses_exchange_display():
    from src.providers.discovery_base import CompanyCandidate

    candidate = CompanyCandidate(
        symbol="MSFT",
        name="Microsoft Corporation",
        provider_exchange="NMS",
        exchange_display="NasdaqGS",
    )

    assert candidate_label(candidate) == (
        "Microsoft Corporation | MSFT | NasdaqGS"
    )


def test_candidate_label_falls_back_to_provider_exchange():
    from src.providers.discovery_base import CompanyCandidate

    candidate = CompanyCandidate(
        symbol="EX",
        name="Example Company",
        provider_exchange="TEST",
    )

    assert candidate_label(candidate) == (
        "Example Company | EX | TEST"
    )


def test_render_company_candidate_preserves_identity(
    monkeypatch,
):
    from src.providers.discovery_base import CompanyCandidate

    candidate = CompanyCandidate(
        symbol="MSFT",
        name="Microsoft Corporation",
        provider_exchange="NMS",
        exchange_display="NasdaqGS",
        currency="USD",
        sector="Technology",
        industry="Software - Infrastructure",
        country="United States",
    )

    subheaders = []
    writes = []
    captions = []
    metrics = []

    class MetricColumn:
        def metric(self, label, value, **kwargs):
            metrics.append((label, value))

    monkeypatch.setattr(
        "streamlit_app.st.subheader",
        subheaders.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.write",
        writes.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.caption",
        captions.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.columns",
        lambda count: tuple(
            MetricColumn()
            for _ in range(count)
        ),
    )

    render_company_candidate(candidate)

    assert subheaders == [
        "Microsoft Corporation"
    ]
    assert metrics == [
        ("S\u00edmbolo", "MSFT"),
        ("Mercado", "NasdaqGS"),
        ("Moneda", "USD"),
        ("Pa\u00eds", "United States"),
    ]
    assert writes == [
        "**Sector:** Technology",
        "**Industria:** Software - Infrastructure",
    ]
    assert len(captions) == 1

def test_build_publication_date_provider_skips_missing_user_agent(
    monkeypatch,
):
    class SettingsStub:
        sec_user_agent = None

    monkeypatch.setattr(
        "streamlit_app.settings",
        SettingsStub(),
    )

    assert build_publication_date_provider() is None


def test_render_coverage_preserves_pit_state(
    monkeypatch,
):
    from datetime import date
    from src.coverage import CompanyCoverage
    from src.metrics import FinancialMetric

    coverage = CompanyCoverage(
        company_id=1,
        as_of_date=date(2026, 9, 24),
        price_available=True,
        fundamental_snapshot_available=False,
        fundamental_growth_available=False,
        forward_eps_period=date(2027, 6, 30),
        estimate_count=1,
        dividend_count=10,
        missing_snapshot_metrics=(
            FinancialMetric.REVENUE,
        ),
        missing_growth_metrics=(
            FinancialMetric.REVENUE,
            FinancialMetric.EPS,
        ),
    )

    subheaders = []
    captions = []
    writes = []
    metrics = []

    class MetricColumn:
        def metric(self, label, value, **kwargs):
            metrics.append((label, value))

    monkeypatch.setattr(
        "streamlit_app.st.subheader",
        subheaders.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.caption",
        captions.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.write",
        writes.append,
    )
    monkeypatch.setattr(
        "streamlit_app.st.columns",
        lambda count: tuple(
            MetricColumn()
            for _ in range(count)
        ),
    )

    render_coverage(coverage)

    assert subheaders == [
        "Cobertura a fecha de an\u00e1lisis"
    ]
    assert metrics == [
        ("Disponibilidad", "S\u00f3lo valoraci\u00f3n"),
        ("Precio", "Disponible"),
        ("BPA estimado", "2027-06-30"),
        ("Fundamentales PIT", "Faltantes"),
    ]
    assert captions == [
        "Estimaciones almacenadas: 1 | "
        "Dividendos almacenados: 10"
    ]
    assert writes == [
        "**M\u00e9tricas PIT faltantes:** eps, revenue"
    ]

def test_percentage_ui_domain_conversion():
    from streamlit_app import (
        percentage_from_domain,
        percentage_to_domain,
    )

    assert percentage_to_domain(5.0) == 0.05
    assert percentage_to_domain(2.0) == 0.02
    assert percentage_to_domain(10.0) == 0.10

    assert percentage_from_domain(0.05) == 5.0
    assert percentage_from_domain(0.02) == 2.0
    assert percentage_from_domain(0.10) == 10.0


def test_percentage_ui_domain_round_trip():
    from streamlit_app import (
        percentage_from_domain,
        percentage_to_domain,
    )

    for value in (
        0.0,
        0.02,
        0.05,
        0.10,
        0.1525,
        -0.05,
    ):
        assert (
            percentage_to_domain(
                percentage_from_domain(value)
            )
            == value
        )

def test_company_record_to_config_preserves_identity():
    from src.models import CompanyRecord, FundamentalProfile
    from streamlit_app import company_record_to_config

    company = CompanyRecord(
        company_id=42,
        name="Microsoft Corporation",
        ticker="MSFT",
        symbol="MSFT",
        country="United States",
        fundamental_profile=FundamentalProfile.OPERATING,
        currency="USD",
        exchange="NMS",
        status="active",
    )

    config = company_record_to_config(company)

    assert config is not None
    assert config.name == "Microsoft Corporation"
    assert config.ticker == "MSFT"
    assert config.symbol == "MSFT"
    assert config.exchange == "NMS"
    assert config.currency == "USD"
    assert config.fundamental_profile == "operating"
    assert config.country == "United States"


def test_company_record_to_config_rejects_incomplete_identity():
    from src.models import CompanyRecord, FundamentalProfile
    from streamlit_app import company_record_to_config

    company = CompanyRecord(
        company_id=42,
        name="Incomplete Company",
        ticker="INC",
        symbol=None,
        fundamental_profile=FundamentalProfile.OPERATING,
        currency="USD",
        exchange="NMS",
        status="active",
    )

    assert company_record_to_config(company) is None


def test_radar_company_label_is_unambiguous():
    from src.universe import CompanyConfig
    from streamlit_app import radar_company_label

    company = CompanyConfig(
        name="Microsoft Corporation",
        ticker="MSFT",
        symbol="MSFT",
        exchange="NMS",
        currency="USD",
        fundamental_profile="operating",
        country="United States",
    )

    assert (
        radar_company_label(company)
        == "Microsoft Corporation | MSFT | NMS"
    )

def test_radar_company_key_is_stable():
    from src.universe import CompanyConfig
    from streamlit_app import radar_company_key

    company = CompanyConfig(
        name="Microsoft Corporation",
        ticker="msft",
        symbol="MSFT",
        exchange="nms",
        currency="USD",
    )

    assert radar_company_key(company) == "MSFT::NMS"


def test_select_radar_companies_preserves_universe_order():
    from src.universe import CompanyConfig
    from streamlit_app import (
        radar_company_key,
        select_radar_companies,
    )

    alpha = CompanyConfig(
        name="Alpha",
        ticker="AAA",
        symbol="AAA",
        exchange="TEST",
        currency="EUR",
    )
    beta = CompanyConfig(
        name="Beta",
        ticker="BBB",
        symbol="BBB",
        exchange="TEST",
        currency="EUR",
    )
    gamma = CompanyConfig(
        name="Gamma",
        ticker="CCC",
        symbol="CCC",
        exchange="TEST",
        currency="EUR",
    )

    universe = (alpha, beta, gamma)

    selected = select_radar_companies(
        universe,
        (
            radar_company_key(gamma),
            radar_company_key(alpha),
        ),
    )

    assert selected == (alpha, gamma)


def test_select_radar_companies_allows_empty_selection():
    from src.universe import CompanyConfig
    from streamlit_app import select_radar_companies

    company = CompanyConfig(
        name="Alpha",
        ticker="AAA",
        symbol="AAA",
        exchange="TEST",
        currency="EUR",
    )

    assert select_radar_companies(
        (company,),
        (),
    ) == ()

def test_radar_selector_precedes_execution_button():
    from inspect import getsource

    from streamlit_app import render_radar_page

    source = getsource(render_radar_page)

    selector_position = source.index(
        'st.multiselect('
    )
    button_position = source.index(
        'st.sidebar.button('
    )
    execution_position = source.index(
        'run_dashboard_radar('
    )

    assert selector_position < button_position
    assert button_position < execution_position
    assert "disabled=not selected_universe" in source

def test_run_selected_company_receives_explicit_assumptions():
    from inspect import getsource

    from streamlit_app import run_selected_company

    source = getsource(run_selected_company)

    assert "scenario: ValuationScenario" in source
    assert "target_return: float" in source
    assert "years: int" in source
    assert "scenarios=(scenario,)" in source
    assert "target_return=float(target_return)" in source
    assert "years=int(years)" in source

    assert "eps_growth=0.05" not in source
    assert "dividend_yield=0.02" not in source
    assert "terminal_pe=15.0" not in source
    assert "target_return=0.10" not in source


def test_company_analysis_uses_explicit_user_assumptions():
    from inspect import getsource

    from streamlit_app import render_company_search

    source = getsource(render_company_search)

    assert 'st.subheader("Hip\\u00f3tesis del usuario")' in source
    assert '"Crecimiento anual del BPA (%)"' in source
    assert '"Rentabilidad por dividendo (%)"' in source
    assert '"PER terminal"' in source
    assert '"Rentabilidad anual objetivo (%)"' in source
    assert '"Horizonte en a\\u00f1os"' in source

    assert (
        "eps_growth=percentage_to_domain("
        in source
    )
    assert (
        "dividend_yield=percentage_to_domain("
        in source
    )
    assert "scenario=company_scenario" in source
    assert (
        "target_return=percentage_to_domain("
        in source
    )
    assert "years=int(company_years)" in source

def test_company_analysis_separates_data_assumptions_results():
    from inspect import getsource

    from streamlit_app import render_company_search

    source = getsource(render_company_search)

    assumptions_position = source.index(
        'st.subheader("Hip\\u00f3tesis del usuario")'
    )
    observed_position = source.index(
        'st.header("Datos observados")'
    )
    results_position = source.index(
        'st.header("Resultados calculados")'
    )
    execution_position = source.index(
        "run_selected_company("
    )

    assert assumptions_position < execution_position
    assert execution_position < observed_position
    assert observed_position < results_position

    assert source.index(
        "render_onboarding_result("
    ) > observed_position

    assert source.index(
        "render_coverage("
    ) > observed_position

    assert source.index(
        "render_investment_result("
    ) > results_position

def test_investment_result_exposes_valuation_traceability():
    from inspect import getsource

    from streamlit_app import render_investment_result

    source = getsource(render_investment_result)

    assert "Datos de mercado y estimaci\\u00f3n" in source
    assert '"Earnings yield"' in source
    assert "snapshot.forward_earnings_yield" in source

    assert '"#### Trazabilidad"' in source
    assert '"Fecha del precio"' in source
    assert "snapshot.price_date.isoformat()" in source

    assert '"Ejercicio BPA"' in source
    assert "snapshot.fiscal_period_end.isoformat()" in source

    assert '"Fecha de estimaci\\u00f3n"' in source
    assert "snapshot.estimate_date.isoformat()" in source

    assert '"Analistas"' in source
    assert "snapshot.analyst_count" in source

    assert '"Fecha PIT del an\\u00e1lisis"' in source
    assert "snapshot.as_of_date.isoformat()" in source

def test_investment_result_exposes_interpretable_valuation():
    from inspect import getsource

    from streamlit_app import render_investment_result

    source = getsource(render_investment_result)

    assert "Lectura de la valoraci\\u00f3n" in source
    assert "len(valuation.scenarios) == 1" in source
    assert "scenario = valuation.scenarios[0]" in source

    assert '"Precio actual"' in source
    assert "snapshot.price" in source

    assert '"Rentabilidad esperada"' in source
    assert "scenario.expected_return" in source

    assert '"Precio requerido"' in source
    assert "scenario.required_price" in source

    assert '"Margen sobre precio"' in source
    assert "scenario.price_margin" in source

    assert "Exigencias del escenario" in source
    assert "scenario.eps_growth" in source
    assert "scenario.required_eps_growth" in source
    assert "scenario.terminal_pe" in source
    assert "scenario.required_pe" in source

    assert "Detalle auditable" in source
    assert "scenario_rows = [" in source
    assert "st.dataframe(" in source
