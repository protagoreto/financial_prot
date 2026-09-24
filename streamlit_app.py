from datetime import date

import streamlit as st

from src.application_flow import run_application_flow
from src.company_discovery import discover_companies
from src.config import settings
from src.dashboard import (
    DashboardRadarResult,
    run_dashboard_radar,
)
from src.db import managed_connection
from src.providers.discovery_base import CompanyCandidate
from src.providers.sec_publication_dates import (
    SecPublicationDateProvider,
)
from src.providers.yahoo import YahooPriceProvider
from src.providers.yahoo_discovery import (
    YahooCompanyDiscoveryProvider,
)
from src.providers.yahoo_dividends import YahooDividendProvider
from src.providers.yahoo_estimates import YahooEstimateProvider
from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)
from src.radar_presentation import RadarPresentation
from src.scenarios import ValuationScenario
from src.streamlit_view import (
    build_radar_table,
    build_unresolved_table,
    financial_help,
    format_decimal,
    format_percentage,
    translate_assessment_level,
    translate_availability,
    translate_onboarding_status,
    translate_onboarding_step,
)
from src.universe import IBEX_UNIVERSE


def candidate_label(
    candidate: CompanyCandidate,
) -> str:
    exchange = (
        candidate.exchange_display
        or candidate.provider_exchange
        or "Mercado desconocido"
    )

    return (
        f"{candidate.name} | "
        f"{candidate.symbol} | "
        f"{exchange}"
    )


def render_company_candidate(
    candidate: CompanyCandidate,
) -> None:
    st.subheader(candidate.name)

    exchange = (
        candidate.exchange_display
        or candidate.provider_exchange
        or "Desconocido"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("S\u00edmbolo", candidate.symbol)
    col2.metric("Mercado", exchange)
    col3.metric("Moneda", candidate.currency or "Desconocida")
    col4.metric("Pa\u00eds", candidate.country or "Desconocido")

    if candidate.sector:
        st.write(f"**Sector:** {candidate.sector}")

    if candidate.industry:
        st.write(f"**Industria:** {candidate.industry}")

    st.caption(
        "Revisa la identidad de la empresa antes de incorporarla "
        "a la base de datos local."
    )


def build_publication_date_provider():
    if not settings.sec_user_agent:
        return None

    return SecPublicationDateProvider(
        user_agent=settings.sec_user_agent
    )


def render_onboarding_result(result) -> None:
    st.subheader("Carga de datos")

    rows = [
        {
            "Etapa": translate_onboarding_step(step.name),
            "Estado": translate_onboarding_status(
                step.status.value
            ),
            "Procesados": step.processed,
            "Detalle": step.detail or "",
        }
        for step in result.steps
    ]

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_coverage(coverage) -> None:
    st.subheader("Cobertura a fecha de an\u00e1lisis")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Disponibilidad",
        translate_availability(
            coverage.availability.value
        ),
        help=financial_help("availability"),
    )
    col2.metric(
        "Precio",
        "Disponible"
        if coverage.price_available
        else "Faltante",
        help=financial_help("price"),
    )
    col3.metric(
        "BPA estimado",
        (
            coverage.forward_eps_period.isoformat()
            if coverage.forward_eps_period
            else "Faltante"
        ),
        help=financial_help("forward_eps"),
    )
    col4.metric(
        "Fundamentales PIT",
        "Disponibles"
        if coverage.fundamentals_available
        else "Faltantes",
        help=financial_help("pit_fundamentals"),
    )

    st.caption(
        f"Estimaciones almacenadas: {coverage.estimate_count} | "
        f"Dividendos almacenados: {coverage.dividend_count}"
    )

    missing = sorted(
        {
            metric.value
            for metric in (
                coverage.missing_snapshot_metrics
                + coverage.missing_growth_metrics
            )
        }
    )

    if missing:
        st.write(
            "**M\u00e9tricas PIT faltantes:** "
            + ", ".join(missing)
        )


def render_investment_result(result) -> None:
    st.subheader("An\u00e1lisis de inversi\u00f3n")

    analysis = result.analysis

    if analysis is None:
        st.warning(
            "No puede construirse un an\u00e1lisis de inversi\u00f3n "
            "con los datos disponibles a la fecha de an\u00e1lisis."
        )
        return

    st.write(
        "**Disponibilidad del an\u00e1lisis:** "
        f"{translate_availability(analysis.availability.value)}"
    )

    valuation = analysis.valuation

    if valuation is not None:
        snapshot = valuation.snapshot

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Precio",
            format_decimal(snapshot.price),
            help=financial_help("price"),
        )
        col2.metric(
            "BPA estimado",
            format_decimal(snapshot.forward_eps, 4),
            help=financial_help("forward_eps"),
        )
        col3.metric(
            "PER estimado",
            (
                format_decimal(snapshot.forward_pe)
                if snapshot.forward_pe is not None
                else "N/D"
            ),
            help=financial_help("forward_pe"),
        )
        col4.metric(
            "Ejercicio BPA",
            snapshot.fiscal_period_end.isoformat(),
            help=financial_help("eps_period"),
        )

        scenario_rows = [
            {
                "Escenario": scenario.name,
                "Crecimiento BPA": format_percentage(
                    scenario.eps_growth
                ),
                "Rentabilidad dividendo": format_percentage(
                    scenario.dividend_yield
                ),
                "PER terminal": format_decimal(
                    scenario.terminal_pe
                ),
                "Rentabilidad esperada": format_percentage(
                    scenario.expected_return
                ),
                "Crecimiento BPA requerido": format_percentage(
                    scenario.required_eps_growth
                ),
                "PER requerido": format_decimal(
                    scenario.required_pe
                ),
                "Precio requerido": format_decimal(
                    scenario.required_price
                ),
                "Margen sobre precio": format_percentage(
                    scenario.price_margin
                ),
            }
            for scenario in valuation.scenarios
        ]

        st.dataframe(
            scenario_rows,
            use_container_width=True,
            hide_index=True,
        )

        with st.expander(
            "\u00bfQu\u00e9 significa cada concepto?"
        ):
            st.markdown(
                "\n".join(
                    (
                        "- **Crecimiento BPA:** "
                        + financial_help("eps_growth"),
                        "- **Rentabilidad por dividendo:** "
                        + financial_help("dividend_yield"),
                        "- **PER terminal:** "
                        + financial_help("terminal_pe"),
                        "- **Rentabilidad esperada:** "
                        + financial_help("expected_return"),
                        "- **Crecimiento BPA requerido:** "
                        + financial_help("required_eps_growth"),
                        "- **PER requerido:** "
                        + financial_help("required_pe"),
                        "- **Precio requerido:** "
                        + financial_help("required_price"),
                        "- **Margen sobre precio:** "
                        + financial_help("price_margin"),
                    )
                )
            )

    fundamentals = analysis.fundamentals

    if fundamentals is not None:
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Calidad",
            translate_assessment_level(
                fundamentals.quality_level.value
            ),
            help=financial_help("quality"),
        )
        col2.metric(
            "Riesgo",
            translate_assessment_level(
                fundamentals.risk_level.value
            ),
            help=financial_help("risk"),
        )
        col3.metric(
            "Trampa de valor",
            "S\u00ed"
            if fundamentals.value_trap_warning
            else "No",
            help=financial_help("value_trap"),
        )


def run_selected_company(
    candidate: CompanyCandidate,
    fundamental_profile: str,
):
    today = date.today()

    scenario = ValuationScenario(
        name="Base",
        eps_growth=0.05,
        dividend_yield=0.02,
        terminal_pe=15.0,
    )

    with managed_connection(settings.db_path) as connection:
        return run_application_flow(
            connection=connection,
            candidate=candidate,
            exchange=(
                candidate.provider_exchange
                or candidate.exchange_display
                or "UNKNOWN"
            ),
            fundamental_profile=fundamental_profile,
            price_provider=YahooPriceProvider(),
            fundamentals_provider=YahooFundamentalsProvider(),
            estimate_provider=YahooEstimateProvider(),
            dividend_provider=YahooDividendProvider(),
            publication_date_provider=(
                build_publication_date_provider()
            ),
            initial_price_date=date(
                today.year - 5,
                1,
                1,
            ),
            end_date=today,
            as_of_date=today,
            scenarios=(scenario,),
            estimate_date=today,
            target_return=0.10,
            years=5,
        )


def render_company_search() -> None:
    st.title("Empresas")

    st.caption(
        "Busca una empresa cotizada, verifica su identidad y "
        "prep\u00e1rala para el an\u00e1lisis determinista."
    )

    query = st.text_input(
        "Buscar empresa",
        placeholder=(
            "Microsoft, MSFT, Inditex, Coca-Cola..."
        ),
    )

    search_requested = st.button(
        "Buscar",
        type="primary",
    )

    if search_requested:
        if not query.strip():
            st.warning(
                "Introduce el nombre o ticker de una empresa."
            )
        else:
            provider = YahooCompanyDiscoveryProvider()

            try:
                with st.spinner(
                    "Buscando empresas..."
                ):
                    candidates = discover_companies(
                        provider=provider,
                        query=query,
                        max_results=8,
                    )
            except Exception as exc:
                st.error(
                    "La b\u00fasqueda de empresas ha fallado: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                st.session_state[
                    "company_candidates"
                ] = candidates

                st.session_state.pop(
                    "selected_company",
                    None,
                )

    candidates = st.session_state.get(
        "company_candidates",
        (),
    )

    if not candidates:
        if search_requested and query.strip():
            st.info(
                "No se encontraron empresas cotizadas."
            )

        return

    st.subheader("Resultados de b\u00fasqueda")

    labels = [
        candidate_label(candidate)
        for candidate in candidates
    ]

    selected_index = st.selectbox(
        "Seleccionar empresa",
        options=range(len(candidates)),
        format_func=lambda index: labels[index],
    )

    selected = candidates[selected_index]

    if st.button(
        "Verificar empresa",
    ):
        provider = YahooCompanyDiscoveryProvider()

        try:
            with st.spinner(
                "Cargando datos de la empresa..."
            ):
                enriched = provider.enrich(
                    selected
                )
        except Exception as exc:
            st.error(
                "La verificaci\u00f3n de la empresa ha fallado: "
                f"{type(exc).__name__}: {exc}"
            )
        else:
            st.session_state[
                "selected_company"
            ] = enriched

    enriched = st.session_state.get(
        "selected_company"
    )

    if enriched is not None:
        st.divider()

        render_company_candidate(
            enriched
        )

        profile = st.radio(
            "Perfil fundamental",
            options=(
                "operating",
                "financial",
            ),
            format_func=lambda value: {
                "operating": "Operativa",
                "financial": "Financiera",
            }[value],
            horizontal=True,
            help=(
                "Operativa: empresas no financieras. "
                "Financiera: bancos y otras "
                "entidades financieras."
            ),
        )

        st.session_state[
            "selected_fundamental_profile"
        ] = profile

        st.caption(
            "Hip\u00f3tesis Base de diagn\u00f3stico: crecimiento del BPA 5%, "
            "rentabilidad por dividendo 2%, PER terminal 15, "
            "rentabilidad objetivo 10% y horizonte de 5 a\u00f1os."
        )

        if st.button(
            "Incorporar y analizar",
            type="primary",
        ):
            try:
                with st.spinner(
                    "Descargando datos y construyendo "
                    "el an\u00e1lisis a fecha hist\u00f3rica..."
                ):
                    flow_result = run_selected_company(
                        candidate=enriched,
                        fundamental_profile=profile,
                    )
            except Exception as exc:
                st.error(
                    "El an\u00e1lisis de la empresa ha fallado: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                st.session_state[
                    "company_flow_result"
                ] = flow_result

        flow_result = st.session_state.get(
            "company_flow_result"
        )

        if flow_result is not None:
            st.divider()

            st.success(
                f"{flow_result.company.name} est\u00e1 disponible "
                "en la base de datos local de an\u00e1lisis."
            )

            render_onboarding_result(
                flow_result.onboarding
            )
            render_coverage(
                flow_result.coverage
            )
            render_investment_result(
                flow_result
            )


def render_radar(
    presentation: RadarPresentation,
) -> None:
    st.title("Sistema de Value Investing")

    st.caption(
        "An\u00e1lisis determinista a fecha hist\u00f3rica"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Fecha de an\u00e1lisis",
        presentation.as_of_date.isoformat(),
    )
    col2.metric(
        "Rentabilidad objetivo",
        format_percentage(
            presentation.target_return
        ),
        help=financial_help("target_return"),
    )
    col3.metric(
        "Horizonte",
        f"{presentation.years} a\u00f1os",
        help=financial_help("horizon"),
    )

    st.subheader(
        f"Radar - {presentation.scenario_name}"
    )

    rows = build_radar_table(
        presentation
    )

    if not rows:
        st.info(
            "No hay empresas disponibles en el radar "
            "para este an\u00e1lisis."
        )
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander(
        "\u00bfQu\u00e9 significa cada concepto del radar?"
    ):
        st.markdown(
            "\n".join(
                (
                    "- **Disponibilidad:** "
                    + financial_help("availability"),
                    "- **Calidad:** "
                    + financial_help("quality"),
                    "- **Riesgo:** "
                    + financial_help("risk"),
                    "- **Trampa de valor:** "
                    + financial_help("value_trap"),
                    "- **Rentabilidad esperada:** "
                    + financial_help("expected_return"),
                    "- **Precio requerido:** "
                    + financial_help("required_price"),
                    "- **Margen sobre precio:** "
                    + financial_help("price_margin"),
                    "- **Condici\u00f3n:** indica si, bajo las "
                    "hip\u00f3tesis del escenario, se cumplen "
                    "las condiciones deterministas del objetivo "
                    "de valoraci\u00f3n.",
                )
            )
        )


def render_unresolved(
    result: DashboardRadarResult,
) -> None:
    rows = build_unresolved_table(
        result.unresolved
    )

    if not rows:
        return

    st.subheader("Empresas no resueltas")

    st.caption(
        "Estas empresas no pudieron valorarse porque "
        "no estaban disponibles los datos necesarios "
        "a la fecha de an\u00e1lisis."
    )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_radar_page() -> None:
    st.sidebar.header("Hip\u00f3tesis del radar")

    as_of_date = st.sidebar.date_input(
        "Fecha de an\u00e1lisis",
        value=date.today(),
        help=(
            "Fecha a la que se reconstruye el an\u00e1lisis. "
            "Los fundamentales posteriores no deben utilizarse."
        ),
    )

    scenario_name = st.sidebar.text_input(
        "Nombre del escenario",
        value="Base",
        help=(
            "Nombre descriptivo para identificar el conjunto "
            "de hip\u00f3tesis de valoraci\u00f3n."
        ),
    )

    eps_growth = st.sidebar.number_input(
        "Crecimiento anual del BPA",
        value=0.05,
        step=0.01,
        format="%.4f",
        help=financial_help("eps_growth"),
    )

    dividend_yield = st.sidebar.number_input(
        "Rentabilidad por dividendo",
        value=0.02,
        step=0.01,
        format="%.4f",
        help=financial_help("dividend_yield"),
    )

    terminal_pe = st.sidebar.number_input(
        "PER terminal",
        value=15.0,
        step=0.5,
        min_value=0.01,
        help=financial_help("terminal_pe"),
    )

    target_return = st.sidebar.number_input(
        "Rentabilidad anual objetivo",
        value=0.10,
        step=0.01,
        format="%.4f",
        help=financial_help("target_return"),
    )

    years = st.sidebar.number_input(
        "Horizonte en a\u00f1os",
        value=5,
        step=1,
        min_value=1,
        help=financial_help("horizon"),
    )

    low_net_debt_threshold = st.sidebar.number_input(
        "Umbral de deuda neta / EBITDA",
        value=2.0,
        step=0.25,
        min_value=0.0,
        help=financial_help(
            "low_net_debt_threshold"
        ),
    )

    st.sidebar.caption(
        "Los porcentajes se introducen como decimales: "
        "0,05 equivale al 5% y 0,10 al 10%."
    )

    run_requested = st.sidebar.button(
        "Ejecutar radar",
        type="primary",
    )

    if not run_requested:
        st.title("Radar")

        st.info(
            "Define expl\u00edcitamente las hip\u00f3tesis "
            "del radar en la barra lateral y ejecuta "
            "el an\u00e1lisis determinista."
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


def main() -> None:
    st.set_page_config(
        page_title="Sistema de Value Investing",
        layout="wide",
    )

    page = st.sidebar.radio(
        "Navegaci\u00f3n",
        options=(
            "Empresas",
            "Radar",
        ),
    )

    if page == "Empresas":
        render_company_search()
        return

    render_radar_page()


if __name__ == "__main__":
    main()
