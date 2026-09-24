from src.models import CompanyRecord
from src.providers.publication_dates_base import (
    PublicationDateProvider,
)
from src.providers.sec_publication_dates import (
    SecPublicationDateProvider,
)
from src.publication_date_policy import (
    publication_date_provider_for_company,
)


class GenericPublicationDateProvider(
    PublicationDateProvider
):
    @property
    def name(self) -> str:
        return "generic"

    def get_publication_dates(
        self,
        company_id: int,
        symbol: str,
    ):
        return []


def _company(
    country: str | None,
) -> CompanyRecord:
    return CompanyRecord(
        company_id=1,
        name="Example",
        ticker="ABC",
        symbol="ABC",
        country=country,
        fundamental_profile="operating",
        currency="USD",
        exchange="TEST",
        status="active",
    )


def test_none_provider_remains_none():
    assert (
        publication_date_provider_for_company(
            company=_company("United States"),
            provider=None,
        )
        is None
    )


def test_sec_allowed_for_united_states():
    provider = SecPublicationDateProvider(
        "Example example@example.com"
    )

    result = publication_date_provider_for_company(
        company=_company("United States"),
        provider=provider,
    )

    assert result is provider


def test_sec_country_matching_is_normalized():
    provider = SecPublicationDateProvider(
        "Example example@example.com"
    )

    for country in (
        " united states ",
        "UNITED STATES OF AMERICA",
        "USA",
        "us",
    ):
        result = publication_date_provider_for_company(
            company=_company(country),
            provider=provider,
        )

        assert result is provider


def test_sec_rejected_for_non_us_company():
    provider = SecPublicationDateProvider(
        "Example example@example.com"
    )

    result = publication_date_provider_for_company(
        company=_company("Spain"),
        provider=provider,
    )

    assert result is None


def test_sec_rejected_when_country_unknown():
    provider = SecPublicationDateProvider(
        "Example example@example.com"
    )

    for country in (None, "", "   "):
        result = publication_date_provider_for_company(
            company=_company(country),
            provider=provider,
        )

        assert result is None


def test_generic_provider_is_not_restricted_by_sec_policy():
    provider = GenericPublicationDateProvider()

    result = publication_date_provider_for_company(
        company=_company("Spain"),
        provider=provider,
    )

    assert result is provider
