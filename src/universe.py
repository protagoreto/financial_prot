from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyConfig:
    name: str
    ticker: str
    symbol: str
    exchange: str
    currency: str


IBEX_UNIVERSE: tuple[CompanyConfig, ...] = (
    CompanyConfig(
        name="Industria de Diseño Textil, S.A.",
        ticker="ITX",
        symbol="ITX.MC",
        exchange="BME",
        currency="EUR",
    ),
    CompanyConfig(
        name="Iberdrola, S.A.",
        ticker="IBE",
        symbol="IBE.MC",
        exchange="BME",
        currency="EUR",
    ),
    CompanyConfig(
        name="Repsol, S.A.",
        ticker="REP",
        symbol="REP.MC",
        exchange="BME",
        currency="EUR",
    ),
    CompanyConfig(
        name="Banco Bilbao Vizcaya Argentaria, S.A.",
        ticker="BBVA",
        symbol="BBVA.MC",
        exchange="BME",
        currency="EUR",
    ),
    CompanyConfig(
        name="Banco Santander, S.A.",
        ticker="SAN",
        symbol="SAN.MC",
        exchange="BME",
        currency="EUR",
    ),
)