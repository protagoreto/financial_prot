from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.presentation import AnalysisPresentation
from src.radar_presentation import RadarPresentation
from src.streamlit_view import (
    build_radar_table,
    financial_help,
    format_decimal,
    format_percentage,
    translate_assessment_level,
    translate_availability,
    translate_onboarding_status,
    translate_onboarding_step,
)
from src.value import ValueCondition


def test_build_radar_table_preserves_values():
    analysis = AnalysisPresentation(
        company_id=1,
        name="Example Company",
        ticker="EX",
        exchange="TEST",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        scenario_name="Base",
        expected_return=0.123456,
        required_price=101.2345,
        price_margin=0.06789,
        condition=ValueCondition.TARGET_MET,
    )

    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(analysis,),
    )

    rows = build_radar_table(
        presentation
    )

    assert rows == [
        {
            "Empresa": "Example Company",
            "Ticker": "EX",
            "Mercado": "TEST",
            "Disponibilidad": "Completo",
            "Calidad": "Fuerte",
            "Riesgo": "Bajo",
            "Trampa de valor": "No",
            "Escenario": "Base",
            "Rentabilidad esperada": "12,35%",
            "Precio requerido": "101,23",
            "Margen sobre precio": "6,79%",
            "Condici\u00f3n": "Objetivo cumplido",
        }
    ]


def test_build_radar_table_preserves_missing_values():
    analysis = AnalysisPresentation(
        company_id=1,
        name="Example Company",
        ticker=None,
        exchange=None,
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.INSUFFICIENT,
        quality_level=None,
        risk_level=None,
        value_trap_warning=None,
        scenario_name="Base",
        expected_return=None,
        required_price=None,
        price_margin=None,
        condition=None,
    )

    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(analysis,),
    )

    rows = build_radar_table(
        presentation
    )

    row = rows[0]

    assert row["Ticker"] is None
    assert row["Mercado"] is None
    assert row["Calidad"] is None
    assert row["Riesgo"] is None
    assert row["Trampa de valor"] is None
    assert row["Rentabilidad esperada"] is None
    assert row["Precio requerido"] is None
    assert row["Margen sobre precio"] is None
    assert row["Condici\u00f3n"] is None


def test_build_radar_table_handles_empty_radar():
    presentation = RadarPresentation(
        as_of_date=date(2026, 9, 22),
        target_return=0.10,
        years=5,
        scenario_name="Base",
        analyses=(),
    )

    assert build_radar_table(
        presentation
    ) == []


def test_build_unresolved_table_preserves_issue():
    from src.radar_universe import (
        RadarUniverseIssue,
        RadarUniverseUnresolved,
    )
    from src.streamlit_view import build_unresolved_table
    from src.universe import CompanyConfig

    company = CompanyConfig(
        name="Example Company",
        ticker="EX",
        symbol="EX",
        exchange="TEST",
        currency="EUR",
    )

    unresolved = (
        RadarUniverseUnresolved(
            company=company,
            issue=(
                RadarUniverseIssue
                .FORWARD_EPS_PERIOD_NOT_FOUND
            ),
        ),
    )

    assert build_unresolved_table(unresolved) == [
        {
            "Empresa": "Example Company",
            "Ticker": "EX",
            "Mercado": "TEST",
            "Incidencia": (
                "No se encontr\u00f3 el periodo de BPA estimado"
            ),
        }
    ]


def test_build_unresolved_table_handles_empty_input():
    from src.streamlit_view import build_unresolved_table

    assert build_unresolved_table(()) == []

def test_spanish_financial_formatters():
    assert format_decimal(20.9134) == "20,91"
    assert format_decimal(23.6759, 4) == "23,6759"
    assert format_percentage(0.0021) == "0,21%"
    assert format_percentage(0.1525) == "15,25%"
    assert format_percentage(-0.3724) == "-37,24%"


def test_spanish_financial_translations():
    assert translate_availability("complete") == "Completo"
    assert (
        translate_availability("valuation_only")
        == "S\u00f3lo valoraci\u00f3n"
    )
    assert translate_assessment_level("strong") == "Fuerte"
    assert translate_assessment_level("low") == "Bajo"
    assert translate_onboarding_status("success") == "Correcto"
    assert translate_onboarding_status("failed") == "Fallido"
    assert translate_onboarding_step("prices") == "Precios"
    assert (
        translate_onboarding_step("publication_dates")
        == "Fechas de publicaci\u00f3n"
    )


def test_financial_help_defines_core_terms():
    for key in (
        "price",
        "forward_eps",
        "forward_pe",
        "terminal_pe",
        "expected_return",
        "required_eps_growth",
        "required_pe",
        "required_price",
        "price_margin",
        "pit_fundamentals",
        "quality",
        "risk",
        "value_trap",
    ):
        assert financial_help(key)
