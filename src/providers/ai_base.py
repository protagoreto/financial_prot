from abc import ABC, abstractmethod

from src.ai import (
    AIAnalysisContext,
    AIAnalysisNarrative,
)


class AIProvider(ABC):
    """
    Common interface for AI narrative providers.

    Providers may interpret deterministic analysis context,
    but must not replace or modify financial calculations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_analysis(
        self,
        context: AIAnalysisContext,
    ) -> AIAnalysisNarrative:
        """
        Generate narrative interpretation from deterministic
        financial analysis context.
        """
        raise NotImplementedError
