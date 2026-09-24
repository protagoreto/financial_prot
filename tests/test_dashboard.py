from datetime import date
from pathlib import Path

from src.dashboard import run_dashboard_radar
from src.db import connect, managed_connection, initialize_database
from src.ingestion import get_or_create_company
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


def test_run_dashboard_radar_preserves_unresolved_company(
    tmp_path: Path,
):
    db_path = tmp_path / "dashboard.sqlite"

    initialize_database(db_path)

    company = CompanyConfig(
        name="Example Company",
        ticker="EX",
        symbol="EX",
        exchange="TEST",
        currency="EUR",
    )

    with managed_connection(db_path) as connection:
        get_or_create_company(
            connection=connection,
            name=company.name,
            ticker=company.ticker,
            exchange=company.exchange,
            currency=company.currency,
        )

    result = run_dashboard_radar(
        db_path=db_path,
        universe=(company,),
        as_of_date=date(2026, 9, 22),
        scenarios=(
            ValuationScenario(
                name="Base",
                eps_growth=0.05,
                dividend_yield=0.02,
                terminal_pe=15.0,
            ),
        ),
        scenario_name="Base",
        model_version="m12.3-test",
        data_version="test-data",
    )

    assert result.presentation.as_of_date == date(
        2026,
        9,
        22,
    )
    assert result.presentation.scenario_name == "Base"
    assert result.presentation.analyses == ()

    assert len(result.unresolved) == 1
    assert result.unresolved[0].company == company
    assert (
        result.unresolved[0].issue.value
        == "forward_eps_period_not_found"
    )
