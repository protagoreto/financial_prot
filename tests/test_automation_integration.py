from pathlib import Path
from unittest.mock import patch

from scripts.automation import main
from src.db import connect
from src.universe import CompanyConfig


TEST_COMPANY = CompanyConfig(
    name="Missing Test Company",
    ticker="MISS",
    symbol="MISS.MC",
    exchange="BME",
    currency="EUR",
)


def test_radar_cli_end_to_end_persists_success_for_unresolved_company(
    tmp_path: Path,
):
    db_path = tmp_path / "automation.sqlite"

    with patch(
        "scripts.automation.IBEX_UNIVERSE",
        (TEST_COMPANY,),
    ):
        exit_code = main(
            [
                "--db-path",
                str(db_path),
                "radar",
                "--as-of-date",
                "2026-09-22",
                "--model-version",
                "m9.7-integration",
                "--data-version",
                "integration-data",
                "--scenario",
                "Base",
                "0.05",
                "0.02",
                "15.0",
            ]
        )

    assert exit_code == 0

    with connect(db_path) as connection:
        analysis_runs = connection.execute(
            """
            SELECT
                model_version,
                data_version,
                company_id,
                status,
                execution_time,
                error
            FROM analysis_runs
            ORDER BY run_id
            """
        ).fetchall()

        company_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM companies
            """
        ).fetchone()["count"]

    assert len(analysis_runs) == 1

    run = analysis_runs[0]

    assert run["model_version"] == "m9.7-integration"
    assert run["data_version"] == "integration-data"
    assert run["company_id"] is None
    assert run["status"] == "success"
    assert run["execution_time"] >= 0
    assert run["error"] is None

    assert company_count == 0
