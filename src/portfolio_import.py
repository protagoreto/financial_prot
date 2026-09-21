import csv
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from pydantic import ValidationError

from src.models import (
    PortfolioTransaction,
    PortfolioTransactionType,
)
from src.repository import (
    get_company_id_by_ticker_exchange,
    insert_portfolio_transaction,
)


_REQUIRED_COLUMNS = {
    "external_id",
    "transaction_date",
    "transaction_type",
    "currency",
    "ticker",
    "exchange",
    "quantity",
    "price",
    "amount",
    "fee",
    "tax",
    "note",
}


class PortfolioImportError(ValueError):
    pass


@dataclass(frozen=True)
class PortfolioImportResult:
    rows_read: int
    transactions_processed: int


def import_portfolio_csv(
    connection: sqlite3.Connection,
    csv_path: str | Path,
) -> PortfolioImportResult:
    path = Path(csv_path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise PortfolioImportError(
                "portfolio CSV has no header"
            )

        fieldnames = {
            field.strip()
            for field in reader.fieldnames
            if field is not None
        }

        missing_columns = (
            _REQUIRED_COLUMNS - fieldnames
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )
            raise PortfolioImportError(
                f"portfolio CSV missing columns: {missing}"
            )

        rows = list(reader)

    transactions = tuple(
        _parse_row(
            connection=connection,
            row=row,
            row_number=index,
        )
        for index, row in enumerate(
            rows,
            start=2,
        )
    )

    for transaction in transactions:
        insert_portfolio_transaction(
            connection=connection,
            transaction=transaction,
        )

    return PortfolioImportResult(
        rows_read=len(rows),
        transactions_processed=len(transactions),
    )


def _parse_row(
    connection: sqlite3.Connection,
    row: dict[str, str | None],
    row_number: int,
) -> PortfolioTransaction:
    external_id = _required_text(
        row=row,
        field="external_id",
        row_number=row_number,
    )

    transaction_date = _required_text(
        row=row,
        field="transaction_date",
        row_number=row_number,
    )

    transaction_type_text = _required_text(
        row=row,
        field="transaction_type",
        row_number=row_number,
    ).lower()

    currency = _required_text(
        row=row,
        field="currency",
        row_number=row_number,
    ).upper()

    try:
        transaction_type = PortfolioTransactionType(
            transaction_type_text
        )
    except ValueError as exc:
        raise PortfolioImportError(
            f"row {row_number}: invalid transaction_type "
            f"{transaction_type_text!r}"
        ) from exc

    ticker = _optional_text(
        row.get("ticker")
    )

    exchange = _optional_text(
        row.get("exchange")
    )

    company_id = _resolve_company_id(
        connection=connection,
        transaction_type=transaction_type,
        ticker=ticker,
        exchange=exchange,
        row_number=row_number,
    )

    quantity = _optional_float(
        value=row.get("quantity"),
        field="quantity",
        row_number=row_number,
    )

    price = _optional_float(
        value=row.get("price"),
        field="price",
        row_number=row_number,
    )

    amount = _optional_float(
        value=row.get("amount"),
        field="amount",
        row_number=row_number,
    )

    fee = _optional_float(
        value=row.get("fee"),
        field="fee",
        row_number=row_number,
    )

    tax = _optional_float(
        value=row.get("tax"),
        field="tax",
        row_number=row_number,
    )

    note = _optional_text(
        row.get("note")
    )

    try:
        return PortfolioTransaction(
            external_id=external_id,
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            currency=currency,
            company_id=company_id,
            quantity=quantity,
            price=price,
            amount=amount,
            fee=0.0 if fee is None else fee,
            tax=0.0 if tax is None else tax,
            note=note,
        )
    except (ValidationError, ValueError) as exc:
        raise PortfolioImportError(
            f"row {row_number}: {exc}"
        ) from exc


def _resolve_company_id(
    connection: sqlite3.Connection,
    transaction_type: PortfolioTransactionType,
    ticker: str | None,
    exchange: str | None,
    row_number: int,
) -> int | None:
    company_required = transaction_type in {
        PortfolioTransactionType.BUY,
        PortfolioTransactionType.SELL,
        PortfolioTransactionType.DIVIDEND,
    }

    if ticker is None and exchange is None:
        if company_required:
            raise PortfolioImportError(
                f"row {row_number}: "
                "ticker and exchange are required"
            )

        return None

    if ticker is None or exchange is None:
        raise PortfolioImportError(
            f"row {row_number}: "
            "ticker and exchange must be provided together"
        )

    if transaction_type == PortfolioTransactionType.CASH:
        raise PortfolioImportError(
            f"row {row_number}: "
            "cash transaction cannot reference a company"
        )

    company_id = get_company_id_by_ticker_exchange(
        connection=connection,
        ticker=ticker,
        exchange=exchange,
    )

    if company_id is None:
        raise PortfolioImportError(
            f"row {row_number}: unknown company "
            f"{ticker.upper()}@{exchange.upper()}"
        )

    return company_id


def _required_text(
    row: dict[str, str | None],
    field: str,
    row_number: int,
) -> str:
    value = _optional_text(
        row.get(field)
    )

    if value is None:
        raise PortfolioImportError(
            f"row {row_number}: {field} is required"
        )

    return value


def _optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    return normalized


def _optional_float(
    value: str | None,
    field: str,
    row_number: int,
) -> float | None:
    normalized = _optional_text(value)

    if normalized is None:
        return None

    try:
        return float(normalized)
    except ValueError as exc:
        raise PortfolioImportError(
            f"row {row_number}: "
            f"{field} must be numeric"
        ) from exc