import json
from dataclasses import dataclass

from src.ai import AIAnalysisContext
from src.ai_serialization import (
    serialize_ai_analysis_context,
)


AI_SYSTEM_INSTRUCTIONS = """\
You are a narrative layer for a deterministic Value Investing system.

The supplied analysis context is the only financial source of truth.

Rules:
1. Do not calculate or recalculate financial metrics.
2. Do not create, estimate, infer, interpolate, or complete missing financial data.
3. Treat null values as unavailable data. Do not replace them with zero or any estimate.
4. Treat "unknown" conditions as unknown. Do not resolve or reinterpret them.
5. Do not modify or override quality, risk, value-trap, availability, or value conditions.
6. Do not introduce external financial facts, market data, estimates, news, or assumptions.
7. Do not produce BUY, HOLD, SELL, or equivalent investment recommendations.
8. Do not create a new valuation, target price, expected return, risk score, or ranking.
9. You may only explain and summarize information explicitly present in the supplied context.
10. Clearly state relevant data limitations when the supplied context is incomplete.

Return narrative content for exactly these fields:
- summary
- quality_commentary
- risk_commentary
- valuation_commentary
- limitations

The first four fields must contain non-blank text.
"limitations" must be a list of zero or more non-blank strings.
"""


@dataclass(frozen=True)
class AIPrompt:
    instructions: str
    context_json: str

    def is_valid(self) -> bool:
        if not self.instructions.strip():
            return False

        if not self.context_json.strip():
            return False

        try:
            decoded = json.loads(self.context_json)
        except (TypeError, ValueError):
            return False

        return isinstance(decoded, dict)


def build_ai_prompt(
    context: AIAnalysisContext,
) -> AIPrompt:
    serialized = serialize_ai_analysis_context(
        context
    )

    context_json = json.dumps(
        serialized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return AIPrompt(
        instructions=AI_SYSTEM_INSTRUCTIONS,
        context_json=context_json,
    )
