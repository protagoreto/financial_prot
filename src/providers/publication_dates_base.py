from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.metrics import PeriodType


@dataclass(frozen=True)
class PublicationDateRecord:
    company_id: int
    period_end: date
    period_type: PeriodType
    publication_date: date
    source_url: str | None = None

    def __post_init__(self) -> None:
        if self.company_id <= 0:
            raise ValueError("company_id must be positive")

        if self.publication_date < self.period_end:
            raise ValueError(
                "publication_date cannot be earlier than period_end"
            )


class PublicationDateProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ) -> list[PublicationDateRecord]:
        raise NotImplementedError
