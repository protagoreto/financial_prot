from datetime import date

from src.dashboard import DashboardRadarResult
from src.radar_presentation import RadarPresentation
from src.radar_universe import (
    RadarUniverseIssue,
    RadarUniverseUnresolved,
)
from src.universe import CompanyConfig
from streamlit_app import (
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
                "Company": "Example Company",
                "Ticker": "EX",
                "Exchange": "TEST",
                "Issue": "forward_eps_period_not_found",
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
