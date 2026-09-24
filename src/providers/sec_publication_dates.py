import json
from datetime import date
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.metrics import PeriodType
from src.providers.publication_dates_base import (
    PublicationDateProvider,
    PublicationDateRecord,
)


SEC_TICKERS_URL = (
    "https://www.sec.gov/files/company_tickers.json"
)
SEC_SUBMISSIONS_URL = (
    "https://data.sec.gov/submissions/CIK{cik}.json"
)
SEC_ARCHIVES_BASE_URL = (
    "https://www.sec.gov/Archives/edgar/data"
)

SUPPORTED_FORMS = {
    "10-K": PeriodType.ANNUAL,
    "10-Q": PeriodType.QUARTERLY,
}


def normalize_cik(value: int | str) -> str:
    text = str(value).strip()

    if not text or not text.isdigit():
        raise ValueError("CIK must contain digits only")

    number = int(text)

    if number <= 0:
        raise ValueError("CIK must be positive")

    return f"{number:010d}"


def build_filing_url(
    cik: int | str,
    accession_number: str,
    primary_document: str,
) -> str:
    normalized_cik = normalize_cik(cik)
    accession = accession_number.strip()
    document = primary_document.strip()

    if not accession:
        raise ValueError("accession_number is required")

    if not document:
        raise ValueError("primary_document is required")

    accession_compact = accession.replace("-", "")

    if not accession_compact.isdigit():
        raise ValueError(
            "accession_number must contain digits and hyphens only"
        )

    cik_path = str(int(normalized_cik))

    return (
        f"{SEC_ARCHIVES_BASE_URL}/{cik_path}/"
        f"{accession_compact}/{quote(document)}"
    )


def parse_publication_records(
    payload: dict[str, Any],
    company_id: int,
) -> list[PublicationDateRecord]:
    if company_id <= 0:
        raise ValueError("company_id must be positive")

    cik = normalize_cik(payload.get("cik", ""))

    filings = payload.get("filings")
    if not isinstance(filings, dict):
        raise ValueError("SEC submissions payload has no filings object")

    recent = filings.get("recent")
    if not isinstance(recent, dict):
        raise ValueError(
            "SEC submissions payload has no recent filings object"
        )

    forms = recent.get("form")
    report_dates = recent.get("reportDate")
    filing_dates = recent.get("filingDate")
    accessions = recent.get("accessionNumber")
    primary_documents = recent.get("primaryDocument")

    columns = (
        forms,
        report_dates,
        filing_dates,
        accessions,
        primary_documents,
    )

    if not all(isinstance(column, list) for column in columns):
        raise ValueError(
            "SEC submissions payload has invalid recent filing columns"
        )

    lengths = {len(column) for column in columns}

    if len(lengths) != 1:
        raise ValueError(
            "SEC submissions recent filing columns have "
            "different lengths"
        )

    records: list[PublicationDateRecord] = []
    seen: set[tuple[date, PeriodType, date]] = set()

    for (
        form,
        report_date,
        filing_date,
        accession,
        primary_document,
    ) in zip(
        forms,
        report_dates,
        filing_dates,
        accessions,
        primary_documents,
        strict=True,
    ):
        period_type = SUPPORTED_FORMS.get(str(form).strip())

        if period_type is None:
            continue

        report_text = str(report_date).strip()
        filing_text = str(filing_date).strip()

        if not report_text or not filing_text:
            continue

        try:
            period_end = date.fromisoformat(report_text)
            publication_date = date.fromisoformat(filing_text)
        except ValueError as exc:
            raise ValueError(
                "SEC filing contains an invalid ISO date"
            ) from exc

        key = (
            period_end,
            period_type,
            publication_date,
        )

        if key in seen:
            continue

        source_url = build_filing_url(
            cik=cik,
            accession_number=str(accession),
            primary_document=str(primary_document),
        )

        records.append(
            PublicationDateRecord(
                company_id=company_id,
                period_end=period_end,
                period_type=period_type,
                publication_date=publication_date,
                source_url=source_url,
            )
        )

        seen.add(key)

    records.sort(
        key=lambda record: (
            record.period_end,
            record.period_type.value,
            record.publication_date,
        )
    )

    return records


class SecPublicationDateProvider(PublicationDateProvider):
    def __init__(
        self,
        user_agent: str,
        timeout: float = 20.0,
    ) -> None:
        normalized_user_agent = user_agent.strip()

        if not normalized_user_agent:
            raise ValueError("SEC user_agent is required")

        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self._user_agent = normalized_user_agent
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "sec_edgar"

    def _get_json(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": self._user_agent,
            },
        )

        with urlopen(
            request,
            timeout=self._timeout,
        ) as response:
            payload = json.load(response)

        if not isinstance(payload, dict):
            raise ValueError("SEC response must be a JSON object")

        return payload

    def resolve_cik(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol is required")

        payload = self._get_json(SEC_TICKERS_URL)

        matches: list[str] = []

        for entry in payload.values():
            if not isinstance(entry, dict):
                continue

            ticker = str(entry.get("ticker", "")).strip().upper()

            if ticker != normalized_symbol:
                continue

            cik_value = entry.get("cik_str")

            try:
                matches.append(normalize_cik(cik_value))
            except ValueError:
                continue

        unique_matches = sorted(set(matches))

        if not unique_matches:
            raise ValueError(
                f"{normalized_symbol}: SEC CIK unavailable"
            )

        if len(unique_matches) != 1:
            raise ValueError(
                f"{normalized_symbol}: SEC CIK is ambiguous"
            )

        return unique_matches[0]

    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ) -> list[PublicationDateRecord]:
        cik = self.resolve_cik(symbol)

        payload = self._get_json(
            SEC_SUBMISSIONS_URL.format(cik=cik)
        )

        payload_cik = normalize_cik(payload.get("cik", ""))

        if payload_cik != cik:
            raise ValueError(
                f"{symbol}: SEC submissions CIK mismatch"
            )

        return parse_publication_records(
            payload=payload,
            company_id=company_id,
        )
