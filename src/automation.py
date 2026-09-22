from dataclasses import dataclass

from src.assessment import AssessmentPolicy
from src.scenarios import ValuationScenario
from src.universe import CompanyConfig


@dataclass(frozen=True)
class RadarRunConfig:
    universe: tuple[CompanyConfig, ...]
    scenarios: tuple[ValuationScenario, ...]
    target_return: float = 0.10
    years: int = 5
    assessment_policy: AssessmentPolicy = AssessmentPolicy()
    low_net_debt_threshold: float = 2.0

    def is_valid(self) -> bool:
        if not self.universe:
            return False

        if not self.scenarios:
            return False

        if self.target_return <= -1:
            return False

        if self.years <= 0:
            return False

        if not self.assessment_policy.is_valid():
            return False

        if self.low_net_debt_threshold < 0:
            return False

        if not self._has_valid_universe():
            return False

        if not self._has_valid_scenarios():
            return False

        return True

    def _has_valid_universe(self) -> bool:
        identities: set[tuple[str, str]] = set()

        for company in self.universe:
            ticker = company.ticker.strip()
            exchange = company.exchange.strip()

            if not ticker or not exchange:
                return False

            identity = (
                ticker.casefold(),
                exchange.casefold(),
            )

            if identity in identities:
                return False

            identities.add(identity)

        return True

    def _has_valid_scenarios(self) -> bool:
        names: set[str] = set()

        for scenario in self.scenarios:
            name = scenario.name.strip()

            if not name:
                return False

            normalized_name = name.casefold()

            if normalized_name in names:
                return False

            names.add(normalized_name)

            if scenario.eps_growth <= -1:
                return False

            if scenario.dividend_yield <= -1:
                return False

            if scenario.terminal_pe <= 0:
                return False

        return True
