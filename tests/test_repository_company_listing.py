from src.db import initialize_database, managed_connection
from src.ingestion import get_or_create_company
from src.repository import list_active_companies


def test_list_active_companies_returns_persisted_identity(tmp_path):
    db_path = tmp_path / "companies.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        company_id = get_or_create_company(
            connection=connection,
            name="Microsoft Corporation",
            ticker="MSFT",
            symbol="MSFT",
            exchange="NMS",
            currency="USD",
            fundamental_profile="operating",
            country="United States",
        )

        companies = list_active_companies(connection)

    assert len(companies) == 1

    company = companies[0]

    assert company.company_id == company_id
    assert company.name == "Microsoft Corporation"
    assert company.ticker == "MSFT"
    assert company.symbol == "MSFT"
    assert company.exchange == "NMS"
    assert company.currency == "USD"
    assert company.fundamental_profile == "operating"
    assert company.country == "United States"
    assert company.status == "active"


def test_list_active_companies_excludes_inactive_companies(tmp_path):
    db_path = tmp_path / "companies.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        active_id = get_or_create_company(
            connection=connection,
            name="Active Company",
            ticker="ACT",
            symbol="ACT",
            exchange="TEST",
            currency="EUR",
        )

        inactive_id = get_or_create_company(
            connection=connection,
            name="Inactive Company",
            ticker="INA",
            symbol="INA",
            exchange="TEST",
            currency="EUR",
        )

        connection.execute(
            """
            UPDATE companies
            SET status = 'inactive'
            WHERE company_id = ?
            """,
            (inactive_id,),
        )
        connection.commit()

        companies = list_active_companies(connection)

    assert tuple(
        company.company_id
        for company in companies
    ) == (active_id,)


def test_list_active_companies_is_deterministic(tmp_path):
    db_path = tmp_path / "companies.sqlite"
    initialize_database(db_path)

    with managed_connection(db_path) as connection:
        get_or_create_company(
            connection=connection,
            name="Zulu Company",
            ticker="ZZZ",
            symbol="ZZZ",
            exchange="TEST",
            currency="EUR",
        )

        get_or_create_company(
            connection=connection,
            name="Alpha Company",
            ticker="AAA",
            symbol="AAA",
            exchange="TEST",
            currency="EUR",
        )

        companies = list_active_companies(connection)

    assert tuple(
        company.name
        for company in companies
    ) == (
        "Alpha Company",
        "Zulu Company",
    )
