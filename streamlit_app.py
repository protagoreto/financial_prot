from datetime import date

import streamlit as st

from src.config import settings
from src.dashboard import (
    DashboardRadarResult,
    run_dashboard_radar,
)
from src.radar_presentation import RadarPresentation
from src.scenarios import ValuationScenario
from src.streamlit_view import (
    build_radar_table,
    build_unresolved_table,
)
from src.universe import IBEX_UNIVERSE


def render_radar(
    presentation: RadarPresentation,
) -> None:
    st.title("Value Investing System")

    st.caption(
        "Deterministic point-in-time analysis"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "As of",
        presentation.as_of_date.isoformat(),
    )
    col2.metric(
        "Target return",
        presentation.target_return,
    )
    col3.metric(
        "Horizon",
        f"{presentation.years} years",
    )

    st.subheader(
        f"Radar - {presentation.scenario_name}"
    )

    rows = build_radar_table(
        presentation
    )

    if not rows:
        st.info(
            "No radar entries are available "
            "for this analysis."
        )
    else:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )


def render_unresolved(
    result: DashboardRadarResult,
) -> None:
    rows = build_unresolved_table(
        result.unresolved
    )

    if not rows:
        return

    st.subheader("Unresolved companies")

    st.caption(
        "These companies were not valued because "
        "the required point-in-time data was unavailable."
    )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    st.sidebar.header("Radar assumptions")

    as_of_date = st.sidebar.date_input(
        "As-of date",
        value=date.today(),
    )

    scenario_name = st.sidebar.text_input(
        "Scenario name",
        value="Base",
    )

    eps_growth = st.sidebar.number_input(
        "EPS growth",
        value=0.05,
        step=0.01,
        format="%.4f",
    )

    dividend_yield = st.sidebar.number_input(
        "Dividend yield",
        value=0.02,
        step=0.01,
        format="%.4f",
    )

    terminal_pe = st.sidebar.number_input(
        "Terminal P/E",
        value=15.0,
        step=0.5,
        min_value=0.01,
    )

    target_return = st.sidebar.number_input(
        "Target annual return",
        value=0.10,
        step=0.01,
        format="%.4f",
    )

    years = st.sidebar.number_input(
        "Horizon in years",
        value=5,
        step=1,
        min_value=1,
    )

    low_net_debt_threshold = st.sidebar.number_input(
        "Low net debt / EBITDA threshold",
        value=2.0,
        step=0.25,
        min_value=0.0,
    )

    run_requested = st.sidebar.button(
        "Run radar",
        type="primary",
    )

    if not run_requested:
        st.title("Value Investing System")

        st.info(
            "Set explicit radar assumptions in the sidebar "
            "and run the deterministic analysis."
        )
        return

    scenario = ValuationScenario(
        name=scenario_name,
        eps_growth=float(eps_growth),
        dividend_yield=float(dividend_yield),
        terminal_pe=float(terminal_pe),
    )

    try:
        result = run_dashboard_radar(
            db_path=settings.db_path,
            universe=IBEX_UNIVERSE,
            as_of_date=as_of_date,
            scenarios=(scenario,),
            scenario_name=scenario_name,
            model_version="streamlit-m12",
            data_version="local-db",
            target_return=float(target_return),
            years=int(years),
            low_net_debt_threshold=float(
                low_net_debt_threshold
            ),
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    render_radar(
        result.presentation
    )

    render_unresolved(
        result
    )


if __name__ == "__main__":
    main()
