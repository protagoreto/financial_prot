import streamlit as st

from src.radar_presentation import RadarPresentation
from src.streamlit_view import build_radar_table


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
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    st.title("Value Investing System")

    st.info(
        "Dashboard infrastructure is ready. "
        "The deterministic radar runtime will be "
        "connected in the next milestone."
    )


if __name__ == "__main__":
    main()
