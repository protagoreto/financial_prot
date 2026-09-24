import io
import json
from datetime import date

import pytest

import src.providers.sec_publication_dates as sec_module
from src.metrics import PeriodType
from src.providers.sec_publication_dates import (
    SecPublicationDateProvider,
    build_filing_url,
    normalize_cik,
    parse_publication_records,
)


def _submissions_payload():
    return {
        "cik": "789019",
        "name": "MICROSOFT CORP",
        "filings": {
            "recent": {
                "form": [
                    "10-K",
                    "10-Q",
                    "8-K",
                    "10-K/A",
                    "10-Q",
                ],
                "reportDate": [
                    "2025-06-30",
                    "2025-09-30",
                    "2025-10-15",
                    "2024-06-30",
                    "2025-09-30",
                ],
                "filingDate": [
                    "2025-07-30",
                    "2025-10-29",
                    "2025-10-15",
                    "2024-08-01",
                    "2025-10-29",
                ],
                "accessionNumber": [
                    "0000950170-25-100001",
                    "0000950170-25-100002",
                    "0000950170-25-100003",
                    "0000950170-25-100004",
                    "0000950170-25-100002",
                ],
                "primaryDocument": [
                    "msft-20250630.htm",
                    "msft-20250930.htm",
                    "msft-8k.htm",
                    "msft-20240630x10ka.htm",
                    "msft-20250930.htm",
                ],
            }
        },
    }


def test_normalize_cik():
    assert normalize_cik(789019) == "0000789019"
    assert normalize_cik("0000789019") == "0000789019"


@pytest.mark.parametrize(
    "value",
    ["", "ABC", "12A", "0", 0, -1],
)
def test_normalize_cik_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        normalize_cik(value)


def test_build_filing_url():
    assert build_filing_url(
        cik="0000789019",
        accession_number="0000950170-25-100001",
        primary_document="msft-20250630.htm",
    ) == (
        "https://www.sec.gov/Archives/edgar/data/"
        "789019/000095017025100001/msft-20250630.htm"
    )


def test_parse_publication_records_maps_only_original_10k_10q():
    records = parse_publication_records(
        payload=_submissions_payload(),
        company_id=7,
    )

    assert len(records) == 2

    annual = records[0]
    quarterly = records[1]

    assert annual.company_id == 7
    assert annual.period_end == date(2025, 6, 30)
    assert annual.period_type == PeriodType.ANNUAL
    assert annual.publication_date == date(2025, 7, 30)

    assert quarterly.period_end == date(2025, 9, 30)
    assert quarterly.period_type == PeriodType.QUARTERLY
    assert quarterly.publication_date == date(2025, 10, 29)


def test_parse_publication_records_deduplicates():
    records = parse_publication_records(
        payload=_submissions_payload(),
        company_id=1,
    )

    quarterly = [
        record
        for record in records
        if record.period_type == PeriodType.QUARTERLY
    ]

    assert len(quarterly) == 1


def test_parse_publication_records_rejects_misaligned_columns():
    payload = _submissions_payload()
    payload["filings"]["recent"]["filingDate"].pop()

    with pytest.raises(
        ValueError,
        match="different lengths",
    ):
        parse_publication_records(
            payload=payload,
            company_id=1,
        )


def test_parse_publication_records_rejects_bad_date():
    payload = _submissions_payload()
    payload["filings"]["recent"]["reportDate"][0] = "not-a-date"

    with pytest.raises(
        ValueError,
        match="invalid ISO date",
    ):
        parse_publication_records(
            payload=payload,
            company_id=1,
        )


def test_provider_requires_user_agent():
    with pytest.raises(
        ValueError,
        match="user_agent is required",
    ):
        SecPublicationDateProvider(user_agent="   ")


def test_provider_resolves_cik_without_network(monkeypatch):
    provider = SecPublicationDateProvider(
        user_agent="ValueInvestingSystem test@example.com"
    )

    payload = {
        "0": {
            "cik_str": 789019,
            "ticker": "MSFT",
            "title": "MICROSOFT CORP",
        },
        "1": {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "Apple Inc.",
        },
    }

    monkeypatch.setattr(
        provider,
        "_get_json",
        lambda url: payload,
    )

    assert provider.resolve_cik("msft") == "0000789019"


def test_provider_rejects_missing_cik(monkeypatch):
    provider = SecPublicationDateProvider(
        user_agent="ValueInvestingSystem test@example.com"
    )

    monkeypatch.setattr(
        provider,
        "_get_json",
        lambda url: {},
    )

    with pytest.raises(
        ValueError,
        match="SEC CIK unavailable",
    ):
        provider.resolve_cik("NOPE")


def test_provider_get_publication_dates_offline(monkeypatch):
    provider = SecPublicationDateProvider(
        user_agent="ValueInvestingSystem test@example.com"
    )

    tickers_payload = {
        "0": {
            "cik_str": 789019,
            "ticker": "MSFT",
            "title": "MICROSOFT CORP",
        }
    }
    submissions_payload = _submissions_payload()

    def fake_get_json(url):
        if url == sec_module.SEC_TICKERS_URL:
            return tickers_payload

        if url == (
            "https://data.sec.gov/submissions/"
            "CIK0000789019.json"
        ):
            return submissions_payload

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        provider,
        "_get_json",
        fake_get_json,
    )

    records = provider.get_publication_dates(
        company_id=12,
        symbol="MSFT",
    )

    assert len(records) == 2
    assert all(record.company_id == 12 for record in records)


def test_provider_rejects_submissions_cik_mismatch(
    monkeypatch,
):
    provider = SecPublicationDateProvider(
        user_agent="ValueInvestingSystem test@example.com"
    )

    tickers_payload = {
        "0": {
            "cik_str": 789019,
            "ticker": "MSFT",
            "title": "MICROSOFT CORP",
        }
    }
    submissions_payload = _submissions_payload()
    submissions_payload["cik"] = "320193"

    def fake_get_json(url):
        if url == sec_module.SEC_TICKERS_URL:
            return tickers_payload

        return submissions_payload

    monkeypatch.setattr(
        provider,
        "_get_json",
        fake_get_json,
    )

    with pytest.raises(
        ValueError,
        match="CIK mismatch",
    ):
        provider.get_publication_dates(
            company_id=1,
            symbol="MSFT",
        )


class _Response:
    def __init__(self, payload):
        self._buffer = io.BytesIO(
            json.dumps(payload).encode("utf-8")
        )

    def __enter__(self):
        return self._buffer

    def __exit__(self, exc_type, exc, tb):
        self._buffer.close()


def test_http_client_sends_user_agent(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response({"ok": True})

    monkeypatch.setattr(
        sec_module,
        "urlopen",
        fake_urlopen,
    )

    provider = SecPublicationDateProvider(
        user_agent="ValueInvestingSystem test@example.com",
        timeout=7.5,
    )

    assert provider._get_json(
        "https://data.sec.gov/example.json"
    ) == {"ok": True}

    assert (
        captured["request"].get_header("User-agent")
        == "ValueInvestingSystem test@example.com"
    )
    assert (
        captured["request"].get_header("Accept-encoding")
        is None
    )
    assert captured["timeout"] == 7.5
