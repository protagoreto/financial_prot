from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyCandidate:
    symbol: str
    name: str
    provider_exchange: str | None = None
    exchange_display: str | None = None
    quote_type: str | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None


class CompanyDiscoveryProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 8,
    ) -> tuple[CompanyCandidate, ...]:
        raise NotImplementedError

    @abstractmethod
    def enrich(
        self,
        candidate: CompanyCandidate,
    ) -> CompanyCandidate:
        raise NotImplementedError
