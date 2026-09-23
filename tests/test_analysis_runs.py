from pathlib import Path

import pytest
from pydantic import ValidationError

from src.db import connect, initialize_database
from src.models import (
    AnalysisRunRecord,
    AnalysisRunStatus,
)
from src.repository import insert_analysis_run


def test_insert_successful_analysis_run(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    record = AnalysisRunRecord(
        model_version="m9.4-test",
        data_version="data-test",
        status=AnalysisRunStatus.SUCCESS,
        execution_time=1.25,
    )

    with connect(db_path) as connection:
        run_id = insert_analysis_run(
            connection=connection,
            record=record,
        )

        row = connection.execute(
            """
            SELECT *
            FROM analysis_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert row is not None
    assert row["model_version"] == "m9.4-test"
    assert row["data_version"] == "data-test"
    assert row["company_id"] is None
    assert row["status"] == "success"
    assert row["execution_time"] == pytest.approx(1.25)
    assert row["error"] is None
    assert row["timestamp"] is not None


def test_insert_failed_analysis_run(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    record = AnalysisRunRecord(
        model_version="m9.4-test",
        data_version="data-test",
        status=AnalysisRunStatus.FAILED,
        execution_time=0.5,
        error="Radar execution failed.",
    )

    with connect(db_path) as connection:
        run_id = insert_analysis_run(
            connection=connection,
            record=record,
        )

        row = connection.execute(
            """
            SELECT *
            FROM analysis_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert row is not None
    assert row["status"] == "failed"
    assert row["error"] == "Radar execution failed."
    assert row["execution_time"] == pytest.approx(0.5)


def test_analysis_run_can_reference_company(
    tmp_path: Path,
):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with connect(db_path) as connection:
        company_id = connection.execute(
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
        ).lastrowid
        connection.commit()

        run_id = insert_analysis_run(
            connection=connection,
            record=AnalysisRunRecord(
                model_version="m9.4-test",
                data_version="data-test",
                company_id=company_id,
                status=AnalysisRunStatus.SUCCESS,
            ),
        )

        row = connection.execute(
            """
            SELECT company_id
            FROM analysis_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert row["company_id"] == company_id


def test_successful_analysis_run_rejects_error():
    with pytest.raises(
        ValidationError,
        match="successful analysis run cannot contain error",
    ):
        AnalysisRunRecord(
            model_version="m9.4-test",
            data_version="data-test",
            status=AnalysisRunStatus.SUCCESS,
            error="Unexpected error.",
        )


def test_failed_analysis_run_requires_error():
    with pytest.raises(
        ValidationError,
        match="failed analysis run requires error",
    ):
        AnalysisRunRecord(
            model_version="m9.4-test",
            data_version="data-test",
            status=AnalysisRunStatus.FAILED,
        )


def test_analysis_run_rejects_negative_execution_time():
    with pytest.raises(ValidationError):
        AnalysisRunRecord(
            model_version="m9.4-test",
            data_version="data-test",
            status=AnalysisRunStatus.SUCCESS,
            execution_time=-0.01,
        )


def test_failed_analysis_run_rejects_empty_error():
    with pytest.raises(
        ValidationError,
        match="failed analysis run requires error",
    ):
        AnalysisRunRecord(
            model_version="m14.3-test",
            data_version="data-test",
            status=AnalysisRunStatus.FAILED,
            error="",
        )


def test_failed_analysis_run_rejects_whitespace_error():
    with pytest.raises(
        ValidationError,
        match="failed analysis run requires error",
    ):
        AnalysisRunRecord(
            model_version="m14.3-test",
            data_version="data-test",
            status=AnalysisRunStatus.FAILED,
            error="   ",
        )
