from abc import ABC, abstractmethod

from src.messaging import OutboundMessage


class MessageProvider(ABC):
    """
    Common interface for outbound message providers.

    Providers receive only a prepared outbound message.
    They do not access financial data or perform analysis.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name.
        """
        raise NotImplementedError

    @abstractmethod
    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        """
        Send a validated outbound message.
        """
        raise NotImplementedError
