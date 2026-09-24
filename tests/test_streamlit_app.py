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
