from abc import ABC, abstractmethod
from datetime import date

from src.models import PriceRecord


class PriceProvider(ABC):
    """
    Common interface for all market price providers.

    Every provider must transform its external data into
    validated PriceRecord objects before returning them.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name.
        """
        raise NotImplementedError

    @abstractmethod
    def get_prices(
        self,
        company_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceRecord]:
        """
        Return normalized prices for the requested period.

        start_date and end_date are inclusive.
        """
        raise NotImplementedError