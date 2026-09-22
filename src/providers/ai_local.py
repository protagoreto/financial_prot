import json
from typing import Any

from src.ai import AIAnalysisNarrative
from src.ai_prompt import AIPrompt
from src.providers.ai_base import AIProvider


class LocalAIProvider(AIProvider):
    """
    Zero-cost deterministic narrative provider.

    This provider uses only the prepared AIPrompt. It performs
    no external calls and introduces no additional financial data.
    """

    @property
    def name(self) -> str:
        return "local"

    def generate_analysis(
        self,
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        if not prompt.is_valid():
            raise ValueError(
                "Local AI provider received an invalid prompt."
            )

        context = json.loads(prompt.context_json)

        company = self._require_dict(
            context,
            "company",
        )
        point_in_time = self._require_dict(
            context,
            "point_in_time",
        )
        analysis = self._require_dict(
            context,
            "analysis",
        )

        quality = self._require_dict(
            analysis,
            "quality",
        )
        risk = self._require_dict(
            analysis,
            "risk",
        )
        value_trap = self._require_dict(
            analysis,
            "value_trap",
        )

        scenarios = analysis.get("scenarios")

        if not isinstance(scenarios, list):
            raise ValueError(
                "AI prompt scenarios must be a list."
            )

        name = self._display_value(
            company.get("name")
        )
        as_of_date = self._display_value(
            point_in_time.get("as_of_date")
        )
        availability = self._display_value(
            analysis.get("availability")
        )

        summary = (
            f"{name}: analysis as of {as_of_date}. "
            f"Availability is {availability}."
        )

        quality_commentary = self._assessment_commentary(
            label="Quality",
            level=quality.get("level"),
            reasons=quality.get("reasons"),
        )

        risk_commentary = self._assessment_commentary(
            label="Risk",
            level=risk.get("level"),
            reasons=risk.get("reasons"),
        )

        valuation_commentary = (
            self._valuation_commentary(scenarios)
        )

        limitations = self._limitations(
            analysis=analysis,
            quality=quality,
            risk=risk,
            value_trap=value_trap,
            scenarios=scenarios,
        )

        return AIAnalysisNarrative(
            summary=summary,
            quality_commentary=quality_commentary,
            risk_commentary=risk_commentary,
            valuation_commentary=valuation_commentary,
            limitations=limitations,
        )

    @staticmethod
    def _require_dict(
        container: dict[str, Any],
        key: str,
    ) -> dict[str, Any]:
        value = container.get(key)

        if not isinstance(value, dict):
            raise ValueError(
                f"AI prompt field '{key}' must be an object."
            )

        return value

    @staticmethod
    def _display_value(value: Any) -> str:
        if value is None:
            return "unavailable"

        return str(value)

    @classmethod
    def _assessment_commentary(
        cls,
        label: str,
        level: Any,
        reasons: Any,
    ) -> str:
        level_text = cls._display_value(level)

        if not isinstance(reasons, list):
            raise ValueError(
                f"{label} reasons must be a list."
            )

        if reasons:
            reason_text = ", ".join(
                str(reason)
                for reason in reasons
            )
        else:
            reason_text = "no reasons supplied"

        return (
            f"{label} level is {level_text}. "
            f"Reasons: {reason_text}."
        )

    @classmethod
    def _valuation_commentary(
        cls,
        scenarios: list[Any],
    ) -> str:
        if not scenarios:
            return (
                "No valuation scenarios are available "
                "in the supplied context."
            )

        descriptions: list[str] = []

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                raise ValueError(
                    "Each AI prompt scenario must be an object."
                )

            name = cls._display_value(
                scenario.get("name")
            )
            expected_return = cls._display_value(
                scenario.get("expected_return")
            )
            required_price = cls._display_value(
                scenario.get("required_price")
            )
            price_margin = cls._display_value(
                scenario.get("price_margin")
            )
            condition = cls._display_value(
                scenario.get("condition")
            )

            descriptions.append(
                (
                    f"{name}: expected_return="
                    f"{expected_return}, required_price="
                    f"{required_price}, price_margin="
                    f"{price_margin}, condition={condition}"
                )
            )

        return "Valuation scenarios: " + "; ".join(
            descriptions
        ) + "."

    @staticmethod
    def _limitations(
        analysis: dict[str, Any],
        quality: dict[str, Any],
        risk: dict[str, Any],
        value_trap: dict[str, Any],
        scenarios: list[Any],
    ) -> tuple[str, ...]:
        limitations: list[str] = []

        if analysis.get("availability") != "complete":
            limitations.append(
                "Analysis availability is not complete."
            )

        if quality.get("level") is None:
            limitations.append(
                "Quality assessment is unavailable."
            )

        if risk.get("level") is None:
            limitations.append(
                "Risk assessment is unavailable."
            )

        if value_trap.get("warning") is None:
            limitations.append(
                "Value-trap assessment is unavailable."
            )

        if not scenarios:
            limitations.append(
                "No valuation scenarios are available."
            )

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue

            if scenario.get("condition") == "unknown":
                limitations.append(
                    (
                        "At least one valuation scenario "
                        "has an unknown value condition."
                    )
                )
                break

        return tuple(limitations)
