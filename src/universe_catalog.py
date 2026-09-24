from dataclasses import dataclass
import csv
from pathlib import Path
import sqlite3

from src.ingestion import get_or_create_company
from src.universe import CompanyConfig


VALID_FUNDAMENTAL_PROFILES = frozenset(
    {"operating", "financial"}
)

REQUIRED_COLUMNS = (
    "name",
    "ticker",
    "symbol",
    "exchange",
    "currency",
    "fundamental_profile",
)


@dataclass(frozen=True)
class UniverseSyncResult:
    companies: tuple[CompanyConfig, ...]
    created: int
    existing: int

    @property
    def total(self) -> int:
        return len(self.companies)


def _required(value: str, field: str, row_number: int) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"Row {row_number}: {field} cannot be empty."
        )

    return normalized


def load_universe_catalog(
    path: Path,
) -> tuple[CompanyConfig, ...]:
    if not path.exists():
        raise ValueError(
            f"Universe catalog not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(
                "Universe catalog has no header."
            )

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise ValueError(
                "Universe catalog missing columns: "
                + ", ".join(missing)
            )

        companies: list[CompanyConfig] = []
        identities: set[tuple[str, str]] = set()
        symbols: set[str] = set()

        for row_number, row in enumerate(reader, start=2):
            name = _required(
                row["name"],
                "name",
                row_number,
            )
            ticker = _required(
                row["ticker"],
                "ticker",
                row_number,
            ).upper()
            symbol = _required(
                row["symbol"],
                "symbol",
                row_number,
            )
            exchange = _required(
                row["exchange"],
                "exchange",
                row_number,
            ).upper()
            currency = _required(
                row["currency"],
                "currency",
                row_number,
            ).upper()
            fundamental_profile = _required(
                row["fundamental_profile"],
                "fundamental_profile",
                row_number,
            ).lower()

            if (
                fundamental_profile
                not in VALID_FUNDAMENTAL_PROFILES
            ):
                raise ValueError(
                    f"Row {row_number}: invalid "
                    "fundamental_profile "
                    f"{fundamental_profile!r}."
                )

            identity = (
                ticker.casefold(),
                exchange.casefold(),
            )

            if identity in identities:
                raise ValueError(
                    f"Row {row_number}: duplicate company "
                    f"identity {ticker}/{exchange}."
                )

            normalized_symbol = symbol.casefold()

            if normalized_symbol in symbols:
                raise ValueError(
                    f"Row {row_number}: duplicate symbol "
                    f"{symbol}."
                )

            identities.add(identity)
            symbols.add(normalized_symbol)

            companies.append(
                CompanyConfig(
                    name=name,
                    ticker=ticker,
                    symbol=symbol,
                    exchange=exchange,
                    currency=currency,
                    fundamental_profile=(
                        fundamental_profile
                    ),
                )
            )

    if not companies:
        raise ValueError(
            "Universe catalog contains no companies."
        )

    return tuple(companies)


def sync_universe_catalog(
    connection: sqlite3.Connection,
    companies: tuple[CompanyConfig, ...],
) -> UniverseSyncResult:
    if not companies:
        raise ValueError(
            "Universe cannot be empty."
        )

    created = 0
    existing = 0

    for company in companies:
        row = connection.execute(
            """
            SELECT company_id
            FROM companies
            WHERE UPPER(ticker) = UPPER(?)
            AND UPPER(exchange) = UPPER(?)
            """,
            (
                company.ticker,
                company.exchange,
            ),
        ).fetchone()

        if row is None:
            get_or_create_company(
                connection=connection,
                name=company.name,
                ticker=company.ticker,
                exchange=company.exchange,
                currency=company.currency,
                fundamental_profile=(
                    company.fundamental_profile
                ),
                symbol=company.symbol,
            )
            created += 1
        else:
            get_or_create_company(
                connection=connection,
                name=company.name,
                ticker=company.ticker,
                exchange=company.exchange,
                currency=company.currency,
                fundamental_profile=(
                    company.fundamental_profile
                ),
                symbol=company.symbol,
            )
            existing += 1

    return UniverseSyncResult(
        companies=companies,
        created=created,
        existing=existing,
    )
