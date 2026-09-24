from src.models import CompanyRecord
from src.providers.publication_dates_base import (
    PublicationDateProvider,
)
from src.providers.sec_publication_dates import (
    SecPublicationDateProvider,
)


SEC_COUNTRIES = frozenset(
    {
        "united states",
        "united states of america",
        "usa",
        "us",
    }
)


def publication_date_provider_for_company(
    company: CompanyRecord,
    provider: PublicationDateProvider | None,
) -> PublicationDateProvider | None:
    if provider is None:
        return None

    if not isinstance(
        provider,
        SecPublicationDateProvider,
    ):
        return provider

    country = (
        company.country.strip().casefold()
        if company.country is not None
        and company.country.strip()
        else None
    )

    if country not in SEC_COUNTRIES:
        return None

    return provider
