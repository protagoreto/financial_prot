from datetime import date
from enum import Enum
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from src.metrics import (
    FinancialMetric,
    PeriodType,
    StatementType,
)


class FinancialRecord(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    company_id: int = Field(gt=0)

    statement_type: StatementType
    metric: FinancialMetric

    value: float
    currency: Optional[str] = None

    period_start: Optional[date] = None
    period_end: date
    period_type: PeriodType

    publication_date: Optional[date] = None
    source_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.period_start
            and self.period_start > self.period_end
        ):
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
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    company_id: int = Field(gt=0)

    metric: FinancialMetric
    value: float
    currency: Optional[str] = None

    fiscal_period_end: date
    estimate_date: date

    analyst_count: Optional[int] = Field(
        default=None,
        ge=0,
    )
    source_id: Optional[int] = Field(
        default=None,
        gt=0,
    )


class PriceRecord(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    company_id: int = Field(gt=0)

    price_date: date

    open: Optional[float] = Field(
        default=None,
        ge=0,
    )
    high: Optional[float] = Field(
        default=None,
        ge=0,
    )
    low: Optional[float] = Field(
        default=None,
        ge=0,
    )
    close: float = Field(gt=0)
    adjusted_close: Optional[float] = Field(
        default=None,
        gt=0,
    )

    volume: Optional[float] = Field(
        default=None,
        ge=0,
    )
    currency: Optional[str] = None

    source_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    @model_validator(mode="after")
    def validate_ohlc(self):
        values = [
            value
            for value in (
                self.open,
                self.high,
                self.low,
                self.close,
            )
            if value is not None
        ]

        if (
            self.high is not None
            and self.high < max(values)
        ):
            raise ValueError(
                "high cannot be lower than another OHLC value"
            )

        if (
            self.low is not None
            and self.low > min(values)
        ):
            raise ValueError(
                "low cannot be higher than another OHLC value"
            )

        return self


class PortfolioTransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    FEE = "fee"
    TAX = "tax"
    CASH = "cash"


class PortfolioTransaction(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    external_id: str = Field(
        min_length=1,
        max_length=200,
    )

    transaction_date: date
    transaction_type: PortfolioTransactionType

    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    company_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    quantity: Optional[float] = Field(
        default=None,
        gt=0,
    )

    price: Optional[float] = Field(
        default=None,
        gt=0,
    )

    amount: Optional[float] = None

    fee: float = Field(
        default=0.0,
        ge=0,
    )

    tax: float = Field(
        default=0.0,
        ge=0,
    )

    note: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_transaction(self):
        if self.transaction_type in {
            PortfolioTransactionType.BUY,
            PortfolioTransactionType.SELL,
        }:
            if self.company_id is None:
                raise ValueError(
                    "buy/sell requires company_id"
                )

            if self.quantity is None:
                raise ValueError(
                    "buy/sell requires quantity"
                )

            if self.price is None:
                raise ValueError(
                    "buy/sell requires price"
                )

            if self.amount is not None:
                raise ValueError(
                    "buy/sell amount is derived "
                    "from quantity and price"
                )

        elif self.transaction_type == (
            PortfolioTransactionType.DIVIDEND
        ):
            if self.company_id is None:
                raise ValueError(
                    "dividend requires company_id"
                )

            if self.amount is None:
                raise ValueError(
                    "dividend requires amount"
                )

            if self.amount <= 0:
                raise ValueError(
                    "dividend amount must be positive"
                )

            if (
                self.quantity is not None
                or self.price is not None
            ):
                raise ValueError(
                    "dividend cannot contain "
                    "quantity or price"
                )

        elif self.transaction_type in {
            PortfolioTransactionType.FEE,
            PortfolioTransactionType.TAX,
        }:
            if self.amount is None:
                raise ValueError(
                    "fee/tax requires amount"
                )

            if self.amount <= 0:
                raise ValueError(
                    "fee/tax amount must be positive"
                )

            if (
                self.quantity is not None
                or self.price is not None
            ):
                raise ValueError(
                    "fee/tax cannot contain "
                    "quantity or price"
                )

        elif self.transaction_type == (
            PortfolioTransactionType.CASH
        ):
            if self.company_id is not None:
                raise ValueError(
                    "cash transaction cannot "
                    "reference a company"
                )

            if self.amount is None:
                raise ValueError(
                    "cash transaction requires amount"
                )

            if self.amount == 0:
                raise ValueError(
                    "cash amount cannot be zero"
                )

            if (
                self.quantity is not None
                or self.price is not None
            ):
                raise ValueError(
                    "cash transaction cannot contain "
                    "quantity or price"
                )

        return self

class PortfolioThesis(BaseModel):
    company_id: int = Field(gt=0)

    effective_date: date

    thesis: str = Field(
        min_length=1,
        max_length=5000,
    )

    risks: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    review_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_portfolio_thesis(
        self,
    ) -> "PortfolioThesis":
        normalized_thesis = self.thesis.strip()

        if not normalized_thesis:
            raise ValueError(
                "thesis cannot be empty"
            )

        self.thesis = normalized_thesis

        if self.risks is not None:
            normalized_risks = self.risks.strip()
            self.risks = (
                normalized_risks
                if normalized_risks
                else None
            )

        if (
            self.review_date is not None
            and self.review_date
            < self.effective_date
        ):
            raise ValueError(
                "review_date cannot be earlier "
                "than effective_date"
            )

        return self