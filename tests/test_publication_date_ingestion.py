from datetime import date

import pytest

from src.db import connect, managed_connection, initialize_database
from src.ingestion import ingest_publication_dates
from src.metrics import PeriodType
from src.providers.publication_dates_base import (
    PublicationDateProvider,
    PublicationDateRecord,
)


class StubPublicationDateProvider(PublicationDateProvider):

    @property
    def name(self) -> str:
        return "stub_publication_dates"

    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ) -> list[PublicationDateRecord]:
        assert symbol == "TEST"

        return [
            PublicationDateRecord(
                company_id=company_id,
                period_end=date(2025, 12, 31),
                period_type=PeriodType.ANNUAL,
                publication_date=date(2026, 2, 20),
                source_url=(
                    "https://example.test/annual-report"
                ),
            ),
            PublicationDateRecord(
                company_id=company_id,
                period_end=date(2024, 12, 31),
                period_type=PeriodType.ANNUAL,
                publication_date=date(2025, 2, 21),
                source_url=(
                    "https://example.test/annual-report-2024"
                ),
            ),
        ]


class EmptyPublicationDateProvider(PublicationDateProvider):

    @property
    def name(self) -> str:
        return "empty_publication_dates"

    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ) -> list[PublicationDateRecord]:
        return []


class WrongCompanyProvider(PublicationDateProvider):

    @property
    def name(self) -> str:
        return "wrong_company"

    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ) -> list[PublicationDateRecord]:
        return [
            PublicationDateRecord(
                company_id=company_id + 1,
                period_end=date(2025, 12, 31),
                period_type=PeriodType.ANNUAL,
                publication_date=date(2026, 2, 20),
            )
        ]


def _create_company(connection) -> int:
    cursor = connection.execute(
        """
        INSERT INTO companies (
            name,
            ticker,
            symbol,
            exchange,
            currency,
            fundamental_profile
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "Test Company",
            "TEST",
            "TEST",
            "TEST",
            "USD",
            "operating",
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def test_publication_date_record_rejects_invalid_date():
    with pytest.raises(
        ValueError,
        match="publication_date cannot be earlier",
    ):
        PublicationDateRecord(
            company_id=1,
            period_end=date(2025, 12, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2025, 12, 30),
        )


def test_publication_date_record_rejects_invalid_company():
    with pytest.raises(
        ValueError,
        match="company_id must be positive",
    ):
        PublicationDateRecord(
            company_id=0,
            period_end=date(2025, 12, 31),
            period_type=PeriodType.ANNUAL,
            publication_date=date(2026, 2, 20),
        )


def test_ingest_publication_dates_persists_provenance(
    tmp_path,
):
    db_path = tmp_path / "publication_dates.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = _create_company(connection)

        inserted = ingest_publication_dates(
            connection=connection,
            provider=StubPublicationDateProvider(),
            company_id=company_id,
            symbol="TEST",
        )

        rows = connection.execute(
            """
            SELECT
                pd.period_end,
                pd.period_type,
                pd.publication_date,
                s.provider,
                s.document_type,
                s.url,
                s.publication_date AS source_publication_date,
                s.confidence
            FROM publication_dates AS pd
            JOIN sources AS s
              ON s.source_id = pd.source_id
            WHERE pd.company_id = ?
            ORDER BY pd.period_end
            """,
            (company_id,),
        ).fetchall()

    assert inserted == 2
    assert len(rows) == 2
    assert rows[0]["period_end"] == "2024-12-31"
    assert rows[1]["period_end"] == "2025-12-31"
    assert rows[1]["publication_date"] == "2026-02-20"
    assert rows[1]["provider"] == "stub_publication_dates"
    assert rows[1]["document_type"] == "publication_date"
    assert (
        rows[1]["url"]
        == "https://example.test/annual-report"
    )
    assert (
        rows[1]["source_publication_date"]
        == "2026-02-20"
    )
    assert rows[1]["confidence"] == "primary"


def test_ingest_publication_dates_is_idempotent(tmp_path):
    db_path = tmp_path / "publication_dates.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = _create_company(connection)
        provider = StubPublicationDateProvider()

        first = ingest_publication_dates(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="TEST",
        )
        second = ingest_publication_dates(
            connection=connection,
            provider=provider,
            company_id=company_id,
            symbol="TEST",
        )

        publication_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM publication_dates
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()["count"]

        source_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM sources
            WHERE provider = ?
            AND document_type = ?
            """,
            (
                "stub_publication_dates",
                "publication_date",
            ),
        ).fetchone()["count"]

    assert first == 2
    assert second == 0
    assert publication_count == 2
    assert source_count == 2


def test_empty_provider_creates_no_source(tmp_path):
    db_path = tmp_path / "publication_dates.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = _create_company(connection)

        inserted = ingest_publication_dates(
            connection=connection,
            provider=EmptyPublicationDateProvider(),
            company_id=company_id,
            symbol="TEST",
        )

        source_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM sources
            """
        ).fetchone()["count"]

    assert inserted == 0
    assert source_count == 0


def test_provider_company_mismatch_is_rejected(tmp_path):
    db_path = tmp_path / "publication_dates.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = _create_company(connection)

        with pytest.raises(
            ValueError,
            match="different company_id",
        ):
            ingest_publication_dates(
                connection=connection,
                provider=WrongCompanyProvider(),
                company_id=company_id,
                symbol="TEST",
            )

        publication_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM publication_dates
            """
        ).fetchone()["count"]

    assert publication_count == 0
