from unittest.mock import patch

from src.providers.discovery_base import CompanyCandidate
from src.providers.yahoo_discovery import (
    YahooCompanyDiscoveryProvider,
)


def test_search_filters_non_equities_and_duplicates():
    quotes = [
        {
            "symbol": "ABC",
            "longname": "ABC Corp",
            "quoteType": "EQUITY",
            "exchange": "NMS",
            "exchDisp": "NASDAQ",
        },
        {
            "symbol": "ABC",
            "longname": "ABC Corp",
            "quoteType": "EQUITY",
            "exchange": "NMS",
        },
        {
            "symbol": "ABC=F",
            "longname": "ABC Future",
            "quoteType": "FUTURE",
            "exchange": "CME",
        },
    ]

    with patch(
        "src.providers.yahoo_discovery.yf.Search"
    ) as search_mock:
        search_mock.return_value.quotes = quotes

        provider = YahooCompanyDiscoveryProvider()
        result = provider.search("ABC")

    assert len(result) == 1
    assert result[0].symbol == "ABC"
    assert result[0].name == "ABC Corp"
    assert result[0].provider_exchange == "NMS"


def test_enrich_adds_metadata():
    candidate = CompanyCandidate(
        symbol="ABC",
        name="ABC",
        provider_exchange="NMS",
        quote_type="EQUITY",
    )

    info = {
        "symbol": "ABC",
        "longName": "ABC Corporation",
        "currency": "USD",
        "exchange": "NMS",
        "quoteType": "EQUITY",
        "sector": "Technology",
        "industry": "Software",
        "country": "United States",
    }

    with patch(
        "src.providers.yahoo_discovery.yf.Ticker"
    ) as ticker_mock:
        ticker_mock.return_value.info = info

        result = (
            YahooCompanyDiscoveryProvider()
            .enrich(candidate)
        )

    assert result.name == "ABC Corporation"
    assert result.currency == "USD"
    assert result.sector == "Technology"
    assert result.industry == "Software"
    assert result.country == "United States"
