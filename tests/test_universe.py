from src.universe import CompanyConfig, IBEX_UNIVERSE


def test_ibex_universe_contains_expected_companies():
    tickers = {
        company.ticker
        for company in IBEX_UNIVERSE
    }

    assert tickers == {
        "ITX",
        "IBE",
        "REP",
        "BBVA",
        "SAN",
    }


def test_universe_tickers_are_unique():
    tickers = [
        company.ticker
        for company in IBEX_UNIVERSE
    ]

    assert len(tickers) == len(set(tickers))


def test_universe_symbols_are_unique():
    symbols = [
        company.symbol
        for company in IBEX_UNIVERSE
    ]

    assert len(symbols) == len(set(symbols))


def test_company_config_is_immutable():
    company = CompanyConfig(
        name="Test Company",
        ticker="TEST",
        symbol="TEST.MC",
        exchange="BME",
        currency="EUR",
    )

    try:
        company.ticker = "OTHER"
        immutable = False
    except AttributeError:
        immutable = True

    assert immutable


def test_ibex_universe_declares_fundamental_profiles():
    profiles = {
        company.ticker: company.fundamental_profile
        for company in IBEX_UNIVERSE
    }

    assert profiles == {
        "ITX": "operating",
        "IBE": "operating",
        "REP": "operating",
        "BBVA": "financial",
        "SAN": "financial",
    }
