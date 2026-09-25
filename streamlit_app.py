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
from src.models import CompanyRecord
from src.radar_presentation import RadarPresentation
from src.repository import list_active_companies
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
from src.universe import CompanyConfig


def percentage_to_domain(value: float) -> float:
    """Convert a percentage entered in the UI to domain decimal form."""
    return float(value) / 100.0


def percentage_from_domain(value: float) -> float:
    """Convert a domain decimal percentage to UI percentage form."""
    return float(value) * 100.0


def company_record_to_config(
    company: CompanyRecord,
) -> CompanyConfig | None:
    required_values = (
        company.ticker,
        company.symbol,
        company.exchange,
        company.currency,
    )

    if any(
        value is None or not value.strip()
        for value in required_values
    ):
        return None

    return CompanyConfig(
        name=company.name,
        ticker=company.ticker.strip(),
        symbol=company.symbol.strip(),
        exchange=company.exchange.strip(),
        currency=company.currency.strip(),
        fundamental_profile=company.fundamental_profile.value,
        country=company.country,
    )


def load_radar_universe() -> tuple[CompanyConfig, ...]:
    with managed_connection(settings.db_path) as connection:
        companies = list_active_companies(connection)

    return tuple(
        config
        for company in companies
        if (config := company_record_to_config(company)) is not None
    )


def radar_company_key(
    company: CompanyConfig,
) -> str:
    return (
        f"{company.ticker.upper()}::"
        f"{company.exchange.upper()}"
    )


def select_radar_companies(
    universe: tuple[CompanyConfig, ...],
    selected_keys: tuple[str, ...] | list[str],
) -> tuple[CompanyConfig, ...]:
    selected = set(selected_keys)

    return tuple(
        company
        for company in universe
        if radar_company_key(company) in selected
    )


def radar_company_label(company: CompanyConfig) -> str:
    return (
        f"{company.name} | "
        f"{company.ticker} | "
        f"{company.exchange}"
    )


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

        st.markdown("#### Datos de mercado y estimaci\u00f3n")

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
            "Earnings yield",
            (
                format_percentage(
                    snapshot.forward_earnings_yield
                )
                if snapshot.forward_earnings_yield is not None
                else "N/D"
            ),
            help=financial_help(
                "forward_earnings_yield"
            ),
        )

        st.markdown("#### Trazabilidad")

        trace_col1, trace_col2, trace_col3 = st.columns(3)

        trace_col1.metric(
            "Fecha del precio",
            snapshot.price_date.isoformat(),
            help=financial_help("price_date"),
        )
        trace_col2.metric(
            "Ejercicio BPA",
            snapshot.fiscal_period_end.isoformat(),
            help=financial_help("eps_period"),
        )
        trace_col3.metric(
            "Fecha de estimaci\u00f3n",
            snapshot.estimate_date.isoformat(),
            help=financial_help("estimate_date"),
        )

        trace_col4, trace_col5 = st.columns(2)

        trace_col4.metric(
            "Analistas",
            (
                str(snapshot.analyst_count)
                if snapshot.analyst_count is not None
                else "N/D"
            ),
            help=financial_help("analyst_count"),
        )
        trace_col5.metric(
            "Fecha PIT del an\u00e1lisis",
            snapshot.as_of_date.isoformat(),
            help=financial_help("as_of_date"),
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
    scenario: ValuationScenario,
    target_return: float,
    years: int,
):
    today = date.today()

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
            target_return=float(target_return),
            years=int(years),
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

        st.subheader("Hip\u00f3tesis del usuario")

        st.caption(
            "Estas hip\u00f3tesis no son datos observados. "
            "Se utilizan para calcular el escenario de valoraci\u00f3n."
        )

        assumption_col1, assumption_col2 = st.columns(2)

        with assumption_col1:
            company_eps_growth_percent = st.number_input(
                "Crecimiento anual del BPA (%)",
                value=percentage_from_domain(0.05),
                step=0.50,
                format="%.2f",
                key="company_eps_growth_percent",
                help=financial_help("eps_growth"),
            )

            company_dividend_yield_percent = st.number_input(
                "Rentabilidad por dividendo (%)",
                value=percentage_from_domain(0.02),
                step=0.25,
                format="%.2f",
                key="company_dividend_yield_percent",
                help=financial_help("dividend_yield"),
            )

            company_terminal_pe = st.number_input(
                "PER terminal",
                value=15.0,
                step=0.5,
                min_value=0.01,
                key="company_terminal_pe",
                help=financial_help("terminal_pe"),
            )

        with assumption_col2:
            company_target_return_percent = st.number_input(
                "Rentabilidad anual objetivo (%)",
                value=percentage_from_domain(0.10),
                step=0.50,
                format="%.2f",
                key="company_target_return_percent",
                help=financial_help("target_return"),
            )

            company_years = st.number_input(
                "Horizonte en a\u00f1os",
                value=5,
                step=1,
                min_value=1,
                key="company_years",
                help=financial_help("horizon"),
            )

        company_scenario = ValuationScenario(
            name="Base",
            eps_growth=percentage_to_domain(
                company_eps_growth_percent
            ),
            dividend_yield=percentage_to_domain(
                company_dividend_yield_percent
            ),
            terminal_pe=float(company_terminal_pe),
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
                        scenario=company_scenario,
                        target_return=percentage_to_domain(
                            company_target_return_percent
                        ),
                        years=int(company_years),
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

            st.header("Datos observados")

            st.caption(
                "Datos obtenidos y almacenados para la empresa, "
                "incluida su cobertura disponible a la fecha "
                "de analisis."
            )

            render_onboarding_result(
                flow_result.onboarding
            )
            render_coverage(
                flow_result.coverage
            )

            st.header("Resultados calculados")

            st.caption(
                "Resultados deterministas calculados a partir de "
                "los datos observados y de las hipotesis definidas "
                "por el usuario."
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

    eps_growth_percent = st.sidebar.number_input(
        "Crecimiento anual del BPA (%)",
        value=percentage_from_domain(0.05),
        step=0.50,
        format="%.2f",
        help=financial_help("eps_growth"),
    )

    dividend_yield_percent = st.sidebar.number_input(
        "Rentabilidad por dividendo (%)",
        value=percentage_from_domain(0.02),
        step=0.25,
        format="%.2f",
        help=financial_help("dividend_yield"),
    )

    terminal_pe = st.sidebar.number_input(
        "PER terminal",
        value=15.0,
        step=0.5,
        min_value=0.01,
        help=financial_help("terminal_pe"),
    )

    target_return_percent = st.sidebar.number_input(
        "Rentabilidad anual objetivo (%)",
        value=percentage_from_domain(0.10),
        step=0.50,
        format="%.2f",
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
        "Introduce los porcentajes en unidades naturales: "
        "5,00 equivale al 5% y 10,00 al 10%."
    )

    radar_universe = load_radar_universe()

    if not radar_universe:
        st.title("Radar")
        st.info(
            "No hay empresas incorporadas con identidad suficiente "
            "para ejecutar el radar. Incorpora primero una empresa "
            "desde la seccion Empresas."
        )
        return

    company_by_key = {
        radar_company_key(company): company
        for company in radar_universe
    }
    available_keys = tuple(company_by_key)

    selected_keys = st.multiselect(
        "Empresas del radar",
        options=available_keys,
        default=available_keys,
        format_func=lambda key: radar_company_label(
            company_by_key[key]
        ),
        help=(
            "Selecciona las empresas incorporadas en la base de "
            "datos que quieres comparar con las mismas hipotesis."
        ),
    )

    selected_universe = select_radar_companies(
        radar_universe,
        selected_keys,
    )

    run_requested = st.sidebar.button(
        "Ejecutar radar",
        type="primary",
        disabled=not selected_universe,
    )

    if not run_requested:
        st.title("Radar")

        if not selected_universe:
            st.info(
                "Selecciona al menos una empresa para ejecutar "
                "el radar."
            )
        else:
            st.info(
                "Selecciona las empresas, define las hipotesis "
                "del radar en la barra lateral y ejecuta "
                "el analisis determinista."
            )

        return

    scenario = ValuationScenario(
        name=scenario_name,
        eps_growth=percentage_to_domain(
            eps_growth_percent
        ),
        dividend_yield=percentage_to_domain(
            dividend_yield_percent
        ),
        terminal_pe=float(terminal_pe),
    )

    try:
        result = run_dashboard_radar(
            db_path=settings.db_path,
            universe=selected_universe,
            as_of_date=as_of_date,
            scenarios=(scenario,),
            scenario_name=scenario_name,
            model_version="streamlit-m12",
            data_version="local-db",
            target_return=percentage_to_domain(
                target_return_percent
            ),
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
