from src.presentation import AnalysisPresentation


def render_analysis_text(
    presentation: AnalysisPresentation,
) -> str:
    identity = presentation.name

    if presentation.ticker is not None:
        identity += f" ({presentation.ticker})"

    lines = [
        identity,
        f"As of: {presentation.as_of_date.isoformat()}",
        (
            "Fiscal period end: "
            f"{presentation.fiscal_period_end.isoformat()}"
        ),
        (
            "Availability: "
            f"{presentation.availability.value}"
        ),
        (
            "Quality: "
            f"{_enum_value(presentation.quality_level)}"
        ),
        (
            "Risk: "
            f"{_enum_value(presentation.risk_level)}"
        ),
        (
            "Value trap warning: "
            f"{_optional_bool(presentation.value_trap_warning)}"
        ),
        f"Scenario: {presentation.scenario_name}",
        (
            "Expected return: "
            f"{_optional_number(presentation.expected_return)}"
        ),
        (
            "Required price: "
            f"{_optional_number(presentation.required_price)}"
        ),
        (
            "Price margin: "
            f"{_optional_number(presentation.price_margin)}"
        ),
        (
            "Value condition: "
            f"{_enum_value(presentation.condition)}"
        ),
        (
            "Target return: "
            f"{presentation.target_return}"
        ),
        f"Horizon: {presentation.years} years",
    ]

    return "\n".join(lines)


def _enum_value(value: object | None) -> str:
    if value is None:
        return "unavailable"

    enum_value = getattr(value, "value", None)

    if enum_value is None:
        raise ValueError(
            "Presentation enum value is invalid."
        )

    return str(enum_value)


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return "unavailable"

    return "true" if value else "false"


def _optional_number(value: float | None) -> str:
    if value is None:
        return "unavailable"

    return str(value)
