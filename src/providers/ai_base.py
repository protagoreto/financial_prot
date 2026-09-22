from abc import ABC, abstractmethod

from src.ai import AIAnalysisNarrative
from src.ai_prompt import AIPrompt


class AIProvider(ABC):
    """
    Common interface for AI narrative providers.

    Providers receive only the prepared AI prompt and must
    return a typed narrative response.
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
        prompt: AIPrompt,
    ) -> AIAnalysisNarrative:
        """
        Generate narrative interpretation from the prepared
        deterministic AI prompt.
        """
        raise NotImplementedError
