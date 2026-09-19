from abc import ABC, abstractmethod

from src.models import FinancialRecord


class FundamentalsProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_annual_financials(
        self,
        company_id: int,
        symbol: str,
    ) -> list[FinancialRecord]:
        raise NotImplementedError