from typing import Any

import yfinance as yf

from src.providers.discovery_base import (
    CompanyCandidate,
    CompanyDiscoveryProvider,
)


class YahooCompanyDiscoveryProvider(
    CompanyDiscoveryProvider
):
    @property
    def name(self) -> str:
        return "yahoo"

    def search(
        self,
        query: str,
        max_results: int = 8,
    ) -> tuple[CompanyCandidate, ...]:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Search query cannot be empty."
            )

        if max_results <= 0:
            raise ValueError(
                "max_results must be positive."
            )

        search = yf.Search(
            normalized_query,
            max_results=max_results,
            news_count=0,
            lists_count=0,
            include_cb=False,
            include_nav_links=False,
            include_research=False,
            include_cultural_assets=False,
        )

        candidates: list[CompanyCandidate] = []
        seen_symbols: set[str] = set()

        for quote in search.quotes:
            if quote.get("quoteType") != "EQUITY":
                continue

            symbol = str(
                quote.get("symbol") or ""
            ).strip()

            if not symbol:
                continue

            normalized_symbol = symbol.casefold()

            if normalized_symbol in seen_symbols:
                continue

            name = str(
                quote.get("longname")
                or quote.get("shortname")
                or symbol
            ).strip()

            candidates.append(
                CompanyCandidate(
                    symbol=symbol,
                    name=name,
                    provider_exchange=_optional_text(
                        quote.get("exchange")
                    ),
                    exchange_display=_optional_text(
                        quote.get("exchDisp")
                    ),
                    quote_type=_optional_text(
                        quote.get("quoteType")
                    ),
                )
            )

            seen_symbols.add(normalized_symbol)

        return tuple(candidates)

    def enrich(
        self,
        candidate: CompanyCandidate,
    ) -> CompanyCandidate:
        info: dict[str, Any] = (
            yf.Ticker(candidate.symbol).info
        )

        quote_type = _optional_text(
            info.get("quoteType")
        )

        if (
            quote_type is not None
            and quote_type != "EQUITY"
        ):
            raise ValueError(
                f"{candidate.symbol} is not an equity."
            )

        return CompanyCandidate(
            symbol=candidate.symbol,
            name=(
                _optional_text(info.get("longName"))
                or _optional_text(info.get("shortName"))
                or candidate.name
            ),
            provider_exchange=(
                _optional_text(info.get("exchange"))
                or candidate.provider_exchange
            ),
            exchange_display=candidate.exchange_display,
            quote_type=quote_type or candidate.quote_type,
            currency=_optional_text(
                info.get("currency")
            ),
            sector=_optional_text(
                info.get("sector")
            ),
            industry=_optional_text(
                info.get("industry")
            ),
            country=_optional_text(
                info.get("country")
            ),
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None
