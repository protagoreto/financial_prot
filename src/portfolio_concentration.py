from dataclasses import dataclass

from src.portfolio import ValuedPortfolioSnapshot


_WEIGHT_TOLERANCE = 1e-12


@dataclass(frozen=True)
class PortfolioConcentrationPosition:
    company_id: int
    market_value: float
    weight: float


@dataclass(frozen=True)
class PortfolioConcentrationSummary:
    currency: str
    total_value: float
    positions_market_value: float
    cash: float
    cash_weight: float | None
    invested_weight: float | None
    position_count: int
    largest_position_weight: float | None
    top_3_weight: float | None
    hhi: float | None
    positions: tuple[PortfolioConcentrationPosition, ...]


def build_portfolio_concentration(
    snapshot: ValuedPortfolioSnapshot,
) -> tuple[PortfolioConcentrationSummary, ...]:
    positions_by_currency = _group_positions_by_currency(
        snapshot
    )

    summaries: list[PortfolioConcentrationSummary] = []

    for currency_summary in snapshot.currency_summaries:
        currency = currency_summary.currency
        total_value = currency_summary.total_value
        positions_market_value = (
            currency_summary.positions_market_value
        )
        cash = currency_summary.cash

        _validate_currency_identity(
            total_value=total_value,
            positions_market_value=positions_market_value,
            cash=cash,
            currency=currency,
        )

        currency_positions = positions_by_currency.get(
            currency,
            (),
        )

        calculated_positions_market_value = sum(
            position.market_value
            for position in currency_positions
        )

        if not _approximately_equal(
            calculated_positions_market_value,
            positions_market_value,
        ):
            raise ValueError(
                f"{currency}: position market values do not "
                "match currency summary"
            )

        if total_value <= 0:
            summaries.append(
                PortfolioConcentrationSummary(
                    currency=currency,
                    total_value=total_value,
                    positions_market_value=(
                        positions_market_value
                    ),
                    cash=cash,
                    cash_weight=None,
                    invested_weight=None,
                    position_count=len(
                        currency_positions
                    ),
                    largest_position_weight=None,
                    top_3_weight=None,
                    hhi=None,
                    positions=(),
                )
            )
            continue

        concentration_positions = tuple(
            sorted(
                (
                    PortfolioConcentrationPosition(
                        company_id=position.company_id,
                        market_value=position.market_value,
                        weight=(
                            position.market_value
                            / total_value
                        ),
                    )
                    for position in currency_positions
                ),
                key=lambda position: (
                    -position.weight,
                    position.company_id,
                ),
            )
        )

        cash_weight = cash / total_value
        invested_weight = (
            positions_market_value / total_value
        )

        _validate_weight_identity(
            invested_weight=invested_weight,
            cash_weight=cash_weight,
            currency=currency,
        )

        position_weights = tuple(
            position.weight
            for position in concentration_positions
        )

        largest_position_weight = (
            position_weights[0]
            if position_weights
            else None
        )

        top_3_weight = (
            sum(position_weights[:3])
            if position_weights
            else None
        )

        hhi = (
            sum(
                weight * weight
                for weight in position_weights
            )
            + cash_weight * cash_weight
        )

        summaries.append(
            PortfolioConcentrationSummary(
                currency=currency,
                total_value=total_value,
                positions_market_value=(
                    positions_market_value
                ),
                cash=cash,
                cash_weight=cash_weight,
                invested_weight=invested_weight,
                position_count=len(
                    concentration_positions
                ),
                largest_position_weight=(
                    largest_position_weight
                ),
                top_3_weight=top_3_weight,
                hhi=hhi,
                positions=concentration_positions,
            )
        )

    return tuple(
        sorted(
            summaries,
            key=lambda summary: summary.currency,
        )
    )


def _group_positions_by_currency(
    snapshot: ValuedPortfolioSnapshot,
) -> dict[str, tuple]:
    grouped: dict[str, list] = {}

    for position in snapshot.positions:
        grouped.setdefault(
            position.currency,
            [],
        ).append(position)

    return {
        currency: tuple(positions)
        for currency, positions in grouped.items()
    }


def _validate_currency_identity(
    total_value: float,
    positions_market_value: float,
    cash: float,
    currency: str,
) -> None:
    expected_total = positions_market_value + cash

    if not _approximately_equal(
        total_value,
        expected_total,
    ):
        raise ValueError(
            f"{currency}: total_value must equal "
            "positions_market_value + cash"
        )


def _validate_weight_identity(
    invested_weight: float,
    cash_weight: float,
    currency: str,
) -> None:
    if not _approximately_equal(
        invested_weight + cash_weight,
        1.0,
    ):
        raise ValueError(
            f"{currency}: invested and cash weights "
            "must sum to 1"
        )


def _approximately_equal(
    left: float,
    right: float,
) -> bool:
    scale = max(
        1.0,
        abs(left),
        abs(right),
    )

    return (
        abs(left - right)
        <= _WEIGHT_TOLERANCE * scale
    )