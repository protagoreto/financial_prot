from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.metrics import FinancialMetric, PeriodType, StatementType


class FinancialRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: int = Field(gt=0)

    statement_type: StatementType
    metric: FinancialMetric

    value: float
    currency: Optional[str] = None

    period_start: Optional[date] = None
    period_end: date
    period_type: PeriodType

    publication_date: Optional[date] = None
    source_id: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.period_start and self.period_start > self.period_end:
            raise ValueError(
                "period_start cannot be later than period_end"
            )

        if (
            self.publication_date
            and self.publication_date < self.period_end
        ):
            raise ValueError(
                "publication_date cannot be earlier than period_end"
            )

        return self


class EstimateRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: int = Field(gt=0)

    metric: FinancialMetric
    value: float
    currency: Optional[str] = None

    fiscal_period_end: date
    estimate_date: date

    analyst_count: Optional[int] = Field(default=None, ge=0)
    source_id: Optional[int] = Field(default=None, gt=0)

class PriceRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: int = Field(gt=0)

    price_date: date

    open: Optional[float] = Field(default=None, ge=0)
    high: Optional[float] = Field(default=None, ge=0)
    low: Optional[float] = Field(default=None, ge=0)
    close: float = Field(gt=0)
    adjusted_close: Optional[float] = Field(default=None, gt=0)

    volume: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None

    source_id: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_ohlc(self):
        values = [
            value
            for value in (self.open, self.high, self.low, self.close)
            if value is not None
        ]

        if self.high is not None and self.high < max(values):
            raise ValueError(
                "high cannot be lower than another OHLC value"
            )

        if self.low is not None and self.low > min(values):
            raise ValueError(
                "low cannot be higher than another OHLC value"
            )

        return self