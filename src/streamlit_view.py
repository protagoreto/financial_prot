from dataclasses import asdict
from typing import Any

from src.presentation import AnalysisPresentation
from src.radar_presentation import RadarPresentation
from src.radar_universe import RadarUniverseUnresolved


def build_radar_table(
    presentation: RadarPresentation,
) -> list[dict[str, Any]]:
    return [
        build_analysis_row(analysis)
        for analysis in presentation.analyses
    ]


def translate_value_condition(value: str) -> str:
    labels = {
        "target_met": "Objetivo cumplido",
        "target_not_met": "Objetivo no cumplido",
        "unknown": "Desconocida",
    }
    return labels.get(value, value)


def translate_radar_issue(value: str) -> str:
    labels = {
        "company_not_found": "Empresa no encontrada",
        "forward_eps_period_not_found": (
            "No se encontr\u00f3 el periodo de BPA estimado"
        ),
        "analysis_failed": "An\u00e1lisis fallido",
    }
    return labels.get(
        value,
        value.replace("_", " ").capitalize(),
    )


def build_analysis_row(
    analysis: AnalysisPresentation,
) -> dict[str, Any]:
    return {
        "Empresa": analysis.name,
        "Ticker": analysis.ticker,
        "Mercado": analysis.exchange,
        "Disponibilidad": translate_availability(
            analysis.availability.value
        ),
        "Calidad": (
            translate_assessment_level(
                analysis.quality_level.value
            )
            if analysis.quality_level is not None
            else None
        ),
        "Riesgo": (
            translate_assessment_level(
                analysis.risk_level.value
            )
            if analysis.risk_level is not None
            else None
        ),
        "Trampa de valor": (
            (
                "S\u00ed"
                if analysis.value_trap_warning
                else "No"
            )
            if analysis.value_trap_warning is not None
            else None
        ),
        "Escenario": analysis.scenario_name,
        "Rentabilidad esperada": (
            format_percentage(analysis.expected_return)
            if analysis.expected_return is not None
            else None
        ),
        "Precio requerido": (
            format_decimal(analysis.required_price)
            if analysis.required_price is not None
            else None
        ),
        "Margen sobre precio": (
            format_percentage(analysis.price_margin)
            if analysis.price_margin is not None
            else None
        ),
        "Condici\u00f3n": (
            translate_value_condition(
                analysis.condition.value
            )
            if analysis.condition is not None
            else None
        ),
    }


def build_unresolved_table(
    unresolved: tuple[RadarUniverseUnresolved, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "Empresa": item.company.name,
            "Ticker": item.company.ticker,
            "Mercado": item.company.exchange,
            "Incidencia": translate_radar_issue(
                item.issue.value
            ),
        }
        for item in unresolved
    ]

FINANCIAL_HELP = {
    "availability": (
        "Indica qu\u00e9 partes del an\u00e1lisis pueden construirse "
        "con los datos disponibles a la fecha seleccionada."
    ),
    "price": (
        "\u00daltimo precio de mercado disponible en o antes de la "
        "fecha de an\u00e1lisis."
    ),
    "forward_eps": (
        "BPA estimado para el pr\u00f3ximo ejercicio fiscal disponible. "
        "BPA significa beneficio por acci\u00f3n."
    ),
    "forward_earnings_yield": (
        "BPA estimado dividido por el precio observado. "
        "Es una rentabilidad de beneficios impl\u00edcita, "
        "no la rentabilidad total esperada de la inversi\u00f3n."
    ),
    "price_date": (
        "Fecha del precio utilizado en la valoraci\u00f3n."
    ),
    "estimate_date": (
        "Fecha de la estimaci\u00f3n de BPA utilizada. "
        "Permite comprobar qu\u00e9 informaci\u00f3n estaba "
        "disponible en la fecha de an\u00e1lisis."
    ),
    "analyst_count": (
        "N\u00famero de analistas asociado a la estimaci\u00f3n "
        "de BPA, cuando el proveedor lo facilita."
    ),
    "as_of_date": (
        "Fecha hist\u00f3rica a la que se reconstruye el "
        "an\u00e1lisis sin utilizar informaci\u00f3n posterior."
    ),
    "forward_pe": (
        "PER estimado: precio actual dividido por el BPA estimado. "
        "Un PER de 20 equivale aproximadamente a pagar 20 veces "
        "ese beneficio por acci\u00f3n estimado."
    ),
    "eps_period": (
        "Fecha de cierre del ejercicio fiscal al que corresponde "
        "el BPA estimado utilizado en la valoraci\u00f3n."
    ),
    "pit_fundamentals": (
        "Fundamentales que eran p\u00fablicamente conocidos en la "
        "fecha de an\u00e1lisis. Evita utilizar informaci\u00f3n "
        "publicada despu\u00e9s."
    ),
    "eps_growth": (
        "Crecimiento anual del BPA supuesto para el escenario. "
        "Es una hip\u00f3tesis de valoraci\u00f3n, no un dato observado."
    ),
    "dividend_yield": (
        "Rentabilidad anual por dividendo supuesta en el escenario, "
        "expresada como porcentaje del precio."
    ),
    "terminal_pe": (
        "PER supuesto al final del horizonte de valoraci\u00f3n. "
        "Representa el m\u00faltiplo al que se supone que cotizar\u00e1 "
        "la empresa al terminar el periodo."
    ),
    "expected_return": (
        "Rentabilidad anualizada resultante de combinar crecimiento "
        "del BPA, dividendos y cambio del PER bajo el escenario."
    ),
    "required_eps_growth": (
        "Crecimiento anual del BPA necesario para alcanzar la "
        "rentabilidad objetivo manteniendo las dem\u00e1s hip\u00f3tesis."
    ),
    "required_pe": (
        "PER m\u00e1ximo de compra compatible con la rentabilidad "
        "objetivo dadas las hip\u00f3tesis del escenario."
    ),
    "required_price": (
        "Precio m\u00e1ximo de compra compatible con la rentabilidad "
        "objetivo y las hip\u00f3tesis del escenario."
    ),
    "price_margin": (
        "Diferencia porcentual entre el precio requerido y el precio "
        "actual. Un valor negativo indica que el precio actual est\u00e1 "
        "por encima del precio compatible con el objetivo."
    ),
    "quality": (
        "Evaluaci\u00f3n determinista de las se\u00f1ales fundamentales "
        "de calidad disponibles. No constituye una recomendaci\u00f3n."
    ),
    "risk": (
        "Nivel derivado de las se\u00f1ales fundamentales de riesgo "
        "definidas por la metodolog\u00eda."
    ),
    "value_trap": (
        "Advertencia de posible trampa de valor cuando determinadas "
        "se\u00f1ales fundamentales deterioradas coinciden con aparente "
        "baratura."
    ),
    "target_return": (
        "Rentabilidad anual m\u00ednima exigida utilizada para calcular "
        "el PER y el precio de compra requeridos."
    ),
    "horizon": (
        "N\u00famero de a\u00f1os durante los que se proyecta el "
        "escenario de valoraci\u00f3n."
    ),
    "low_net_debt_threshold": (
        "Umbral de deuda neta sobre EBITDA utilizado por las reglas "
        "de evaluaci\u00f3n de riesgo para empresas operativas."
    ),
}


def financial_help(key: str) -> str:
    return FINANCIAL_HELP[key]


def format_decimal(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_percentage(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value * 100:.{decimals}f}%".replace(".", ",")


def translate_availability(value: str) -> str:
    labels = {
        "complete": "Completo",
        "valuation_only": "S\u00f3lo valoraci\u00f3n",
        "fundamentals_only": "S\u00f3lo fundamentales",
        "insufficient": "Insuficiente",
    }
    return labels.get(value, value)


FUNDAMENTAL_REASON_LABELS = {
    "positive_net_income": "Beneficio neto positivo",
    "positive_free_cash_flow": "Flujo de caja libre positivo",
    "positive_roe": "ROE positivo",
    "low_net_debt": "Deuda neta contenida",
    "positive_roa": "ROA positivo",
    "positive_tangible_book_growth": (
        "Crecimiento positivo del valor contable tangible"
    ),
    "revenue_decline": "Descenso de ingresos",
    "eps_decline": "Descenso del BPA",
    "free_cash_flow_decline": (
        "Descenso del flujo de caja libre"
    ),
    "margin_contraction": "Contracci\u00f3n de m\u00e1rgenes",
    "share_dilution": "Diluci\u00f3n de acciones",
    "net_interest_income_decline": (
        "Descenso del margen de intereses"
    ),
    "tangible_book_decline": (
        "Descenso del valor contable tangible"
    ),
}


def translate_fundamental_reason(reason: str) -> str:
    return FUNDAMENTAL_REASON_LABELS.get(
        reason,
        reason.replace("_", " ").capitalize(),
    )


def translate_assessment_level(value: str) -> str:
    labels = {
        "strong": "Fuerte",
        "mixed": "Mixta",
        "weak": "D\u00e9bil",
        "low": "Bajo",
        "moderate": "Moderado",
        "high": "Alto",
    }
    return labels.get(value, value)


def translate_onboarding_status(value: str) -> str:
    labels = {
        "success": "Correcto",
        "unavailable": "No disponible",
        "failed": "Fallido",
    }
    return labels.get(value, value)


def translate_onboarding_step(value: str) -> str:
    labels = {
        "prices": "Precios",
        "financials": "Fundamentales",
        "forward_eps": "BPA estimado",
        "dividends": "Dividendos",
        "publication_dates": "Fechas de publicaci\u00f3n",
    }
    return labels.get(value, value)
