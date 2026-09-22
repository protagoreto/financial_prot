from datetime import date
from pathlib import Path

import pytest

from src.db import connect, initialize_database
from src.metrics import FinancialMetric, PeriodType, StatementType
from src.models import EstimateRecord, FinancialRecord, PriceRecord
from src.repository import (
    get_company_by_id,
    get_financial_for_period_on_or_before,
    get_latest_estimate_on_or_before,
    get_latest_financial_on_or_before,
    get_next_estimate_period_on_or_after,
    get_verified_publication_date,
    insert_estimate_record,
    insert_financial_record,
    insert_price_record,
    insert_publication_date,
)
def create_company(connection) -> int:
    cursor = connection.execute(
        """
        INSERT INTO companies (
            name,
            ticker,
            exchange,
            currency
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "Test Company",
            "TEST",
            "TESTEX",
            "EUR",
        ),
    )

    connection.commit()
    return cursor.lastrowid


def test_insert_financial_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = FinancialRecord(
            company_id=company_id,
            statement_type="income_statement",
            metric="net_income",
            value=100.0,
            currency="EUR",
            period_start="2025-01-01",
            period_end="2025-12-31",
            period_type="annual",
            publication_date="2026-02-01",
        )

        record_id = insert_financial_record(connection, record)

        row = connection.execute(
            """
            SELECT *
            FROM financials
            WHERE financial_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["metric"] == "net_income"
    assert row["value"] == 100.0
    assert row["period_end"] == "2025-12-31"


def test_insert_estimate_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = EstimateRecord(
            company_id=company_id,
            metric="eps",
            value=2.50,
            currency="EUR",
            fiscal_period_end="2027-12-31",
            estimate_date="2026-09-19",
            analyst_count=12,
        )

        record_id = insert_estimate_record(connection, record)

        row = connection.execute(
            """
            SELECT *
            FROM estimates
            WHERE estimate_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["metric"] == "eps"
    assert row["value"] == 2.50
    assert row["estimate_date"] == "2026-09-19"
    assert row["analyst_count"] == 12

def test_insert_price_record(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.74,
            adjusted_close=51.74,
            volume=6017239,
            currency="EUR",
        )

        record_id = insert_price_record(
            connection,
            record,
        )

        row = connection.execute(
            """
            SELECT *
            FROM prices
            WHERE price_id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row["price_date"] == "2026-09-18"
    assert row["close"] == 51.74
    assert row["adjusted_close"] == 51.74
    assert row["volume"] == 6017239
    assert row["currency"] == "EUR"

def test_insert_price_record_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        first_record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.74,
            adjusted_close=51.74,
            volume=6017239,
            currency="EUR",
        )

        first_id = insert_price_record(
            connection,
            first_record,
        )

        updated_record = PriceRecord(
            company_id=company_id,
            price_date="2026-09-18",
            open=52.30,
            high=52.40,
            low=51.54,
            close=51.75,
            adjusted_close=51.75,
            volume=6018000,
            currency="EUR",
        )

        second_id = insert_price_record(
            connection,
            updated_record,
        )

        rows = connection.execute(
            """
            SELECT *
            FROM prices
            WHERE company_id = ?
            AND price_date = ?
            """,
            (
                company_id,
                "2026-09-18",
            ),
        ).fetchall()

    assert first_id == second_id
    assert len(rows) == 1
    assert rows[0]["close"] == 51.75
    assert rows[0]["volume"] == 6018000

def test_get_latest_price_date_returns_none_without_prices(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        from src.repository import get_latest_price_date

        latest = get_latest_price_date(
            connection,
            company_id,
        )

    assert latest is None


def test_get_latest_price_date_returns_most_recent_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-17",
                close=50.0,
                currency="EUR",
            ),
        )

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-18",
                close=51.0,
                currency="EUR",
            ),
        )

        from src.repository import get_latest_price_date

        latest = get_latest_price_date(
            connection,
            company_id,
        )

    assert latest.isoformat() == "2026-09-18"

def test_get_price_on_or_before_exact_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-18",
                close=51.0,
                currency="EUR",
            ),
        )

        from src.repository import get_price_on_or_before

        price = get_price_on_or_before(
            connection,
            company_id,
            date(2026, 9, 18),
        )

    assert price is not None
    assert price.price_date == date(2026, 9, 18)
    assert price.close == 51.0


def test_get_price_on_or_before_uses_previous_session(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-18",
                close=51.0,
                currency="EUR",
            ),
        )

        from src.repository import get_price_on_or_before

        price = get_price_on_or_before(
            connection,
            company_id,
            date(2026, 9, 20),
        )

    assert price is not None
    assert price.price_date == date(2026, 9, 18)
    assert price.close == 51.0


def test_get_price_on_or_before_returns_none_before_history(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_price_record(
            connection,
            PriceRecord(
                company_id=company_id,
                price_date="2026-09-18",
                close=51.0,
                currency="EUR",
            ),
        )

        from src.repository import get_price_on_or_before

        price = get_price_on_or_before(
            connection,
            company_id,
            date(2026, 9, 17),
        )

    assert price is None

def test_financial_is_not_available_before_publication(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.50,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        financial = get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 2, 25),
            period_type=PeriodType.ANNUAL,
        )

    assert financial is None


def test_financial_is_available_on_publication_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.50,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        financial = get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 2, 26),
            period_type=PeriodType.ANNUAL,
        )

    assert financial is not None
    assert financial.value == 2.50
    assert financial.period_end == date(2025, 12, 31)


def test_financial_query_uses_latest_known_publication(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.00,
                currency="EUR",
                period_end="2024-12-31",
                period_type="annual",
                publication_date="2025-02-27",
            ),
        )

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type="income_statement",
                metric="eps",
                value=2.50,
                currency="EUR",
                period_end="2025-12-31",
                period_type="annual",
                publication_date="2026-02-26",
            ),
        )

        financial = get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 1, 15),
            period_type=PeriodType.ANNUAL,
        )

    assert financial is not None
    assert financial.value == 2.00
    assert financial.period_end == date(2024, 12, 31)

def test_estimate_is_not_available_before_estimate_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.00,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-03-01",
                analyst_count=10,
            ),
        )

        estimate = get_latest_estimate_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            fiscal_period_end=date(2026, 12, 31),
            as_of_date=date(2026, 2, 28),
        )

    assert estimate is None


def test_estimate_is_available_on_estimate_date(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.00,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-03-01",
                analyst_count=10,
            ),
        )

        estimate = get_latest_estimate_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            fiscal_period_end=date(2026, 12, 31),
            as_of_date=date(2026, 3, 1),
        )

    assert estimate is not None
    assert estimate.value == 3.00
    assert estimate.analyst_count == 10


def test_estimate_query_uses_latest_known_revision(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.00,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-03-01",
                analyst_count=10,
            ),
        )

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric="eps",
                value=3.40,
                currency="EUR",
                fiscal_period_end="2026-12-31",
                estimate_date="2026-06-01",
                analyst_count=12,
            ),
        )

        estimate = get_latest_estimate_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            fiscal_period_end=date(2026, 12, 31),
            as_of_date=date(2026, 5, 15),
        )

    assert estimate is not None
    assert estimate.value == 3.00
    assert estimate.estimate_date == date(2026, 3, 1)


def test_financial_without_publication_date_is_not_point_in_time_available(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=(
                    StatementType.INCOME_STATEMENT
                ),
                metric=FinancialMetric.EPS,
                value=2.0,
                currency="EUR",
                period_end="2026-01-31",
                period_type=PeriodType.ANNUAL,
                publication_date=None,
            ),
        )

        result = get_latest_financial_on_or_before(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 12, 31),
            period_type=PeriodType.ANNUAL,
        )

    assert result is None

def test_insert_publication_date_with_provenance(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                retrieved_at,
                document_type,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "official",
                "2026-09-20T10:00:00+00:00",
                "annual_results",
                "primary",
            ),
        ).lastrowid

        publication_date_id = insert_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 3, 11),
            source_id=source_id,
        )

        row = connection.execute(
            """
            SELECT
                pd.period_end,
                pd.period_type,
                pd.publication_date,
                s.provider,
                s.confidence
            FROM publication_dates AS pd
            JOIN sources AS s
                ON s.source_id = pd.source_id
            WHERE pd.publication_date_id = ?
            """,
            (publication_date_id,),
        ).fetchone()

    assert row["period_end"] == "2026-01-31"
    assert row["period_type"] == "annual"
    assert row["publication_date"] == "2026-03-11"
    assert row["provider"] == "official"
    assert row["confidence"] == "primary"

def test_get_verified_publication_date(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                retrieved_at,
                document_type,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "official",
                "2026-09-20T10:00:00+00:00",
                "annual_results",
                "primary",
            ),
        ).lastrowid

        insert_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 3, 11),
            source_id=source_id,
        )

        result = get_verified_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
        )

    assert result == date(2026, 3, 11)

def test_get_verified_publication_date_returns_none_when_unknown(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        result = get_verified_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
        )

    assert result is None


def test_verified_publication_date_controls_point_in_time_access(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        financial_source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                retrieved_at,
                document_type,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "yahoo",
                "2026-09-20T10:00:00+00:00",
                "annual_financials",
                "secondary",
            ),
        ).lastrowid

        publication_source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                retrieved_at,
                document_type,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "official",
                "2026-09-20T10:00:00+00:00",
                "annual_results",
                "primary",
            ),
        ).lastrowid

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=(
                    StatementType.INCOME_STATEMENT
                ),
                metric=FinancialMetric.EPS,
                value=2.0,
                currency="EUR",
                period_end=date(2026, 1, 31),
                period_type=PeriodType.ANNUAL,
                publication_date=None,
                source_id=financial_source_id,
            ),
        )

        insert_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 3, 11),
            source_id=publication_source_id,
        )

        before_publication = (
            get_latest_financial_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                as_of_date=date(2026, 3, 10),
                period_type=PeriodType.ANNUAL,
            )
        )

        on_publication = (
            get_latest_financial_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                as_of_date=date(2026, 3, 11),
                period_type=PeriodType.ANNUAL,
            )
        )

    assert before_publication is None

    assert on_publication is not None
    assert on_publication.value == 2.0
    assert on_publication.publication_date == date(
        2026,
        3,
        11,
    )

def test_insert_publication_date_is_idempotent(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        source_id = connection.execute(
            """
            INSERT INTO sources (
                provider,
                retrieved_at,
                document_type,
                confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "official",
                "2026-09-20T10:00:00+00:00",
                "annual_results",
                "primary",
            ),
        ).lastrowid

        first_id = insert_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 3, 11),
            source_id=source_id,
        )

        second_id = insert_publication_date(
            connection=connection,
            company_id=company_id,
            period_end=date(2026, 1, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 3, 11),
            source_id=source_id,
        )

        count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM publication_dates
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()["count"]

    assert first_id == second_id
    assert count == 1


def test_get_financial_for_period_respects_publication_date(
    tmp_path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_financial_record(
            connection,
            FinancialRecord(
                company_id=company_id,
                statement_type=(
                    StatementType.INCOME_STATEMENT
                ),
                metric=FinancialMetric.EPS,
                value=2.0,
                currency="EUR",
                period_end="2026-01-31",
                period_type=PeriodType.ANNUAL,
                publication_date="2026-03-11",
            ),
        )

        before_publication = (
            get_financial_for_period_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                period_end=date(2026, 1, 31),
                as_of_date=date(2026, 3, 10),
                period_type=PeriodType.ANNUAL,
            )
        )

        on_publication = (
            get_financial_for_period_on_or_before(
                connection=connection,
                company_id=company_id,
                metric=FinancialMetric.EPS,
                period_end=date(2026, 1, 31),
                as_of_date=date(2026, 3, 11),
                period_type=PeriodType.ANNUAL,
            )
        )

    assert before_publication is None

    assert on_publication is not None
    assert on_publication.value == pytest.approx(2.0)
    assert on_publication.period_end == date(
        2026,
        1,
        31,
    )
    assert on_publication.publication_date == date(
        2026,
        3,
        11,
    )


def test_get_company_by_id_returns_company(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        company = get_company_by_id(
            connection=connection,
            company_id=company_id,
        )

    assert company is not None
    assert company.company_id == company_id
    assert company.name == "Test Company"
    assert company.ticker == "TEST"
    assert company.exchange == "TESTEX"
    assert company.currency == "EUR"
    assert company.status == "active"


def test_get_company_by_id_returns_none_when_unknown(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company = get_company_by_id(
            connection=connection,
            company_id=999,
        )

    assert company is None


def test_get_company_by_id_rejects_invalid_id(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(
            ValueError,
            match="positive",
        ):
            get_company_by_id(
                connection=connection,
                company_id=0,
            )


def test_get_next_estimate_period_selects_nearest_forward_period(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric=FinancialMetric.EPS,
                value=2.0,
                fiscal_period_end="2026-12-31",
                estimate_date="2026-09-01",
            ),
        )
        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric=FinancialMetric.EPS,
                value=2.2,
                fiscal_period_end="2027-12-31",
                estimate_date="2026-09-01",
            ),
        )

        result = get_next_estimate_period_on_or_after(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 9, 22),
        )

    assert result == date(2026, 12, 31)


def test_get_next_estimate_period_is_point_in_time(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric=FinancialMetric.EPS,
                value=2.0,
                fiscal_period_end="2026-12-31",
                estimate_date="2026-10-01",
            ),
        )

        result = get_next_estimate_period_on_or_after(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 9, 22),
        )

    assert result is None


def test_get_next_estimate_period_excludes_past_periods(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric=FinancialMetric.EPS,
                value=1.8,
                fiscal_period_end="2025-12-31",
                estimate_date="2025-09-01",
            ),
        )

        result = get_next_estimate_period_on_or_after(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 9, 22),
        )

    assert result is None


def test_get_next_estimate_period_respects_metric(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = create_company(connection)

        insert_estimate_record(
            connection,
            EstimateRecord(
                company_id=company_id,
                metric=FinancialMetric.REVENUE,
                value=1000.0,
                fiscal_period_end="2026-12-31",
                estimate_date="2026-09-01",
            ),
        )

        result = get_next_estimate_period_on_or_after(
            connection=connection,
            company_id=company_id,
            metric=FinancialMetric.EPS,
            as_of_date=date(2026, 9, 22),
        )

    assert result is None


def test_get_next_estimate_period_rejects_invalid_company_id(
    tmp_path: Path,
):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(
            ValueError,
            match="company_id must be positive",
        ):
            get_next_estimate_period_on_or_after(
                connection=connection,
                company_id=0,
                metric=FinancialMetric.EPS,
                as_of_date=date(2026, 9, 22),
            )
