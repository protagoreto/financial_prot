from dataclasses import dataclass
from datetime import date
import sqlite3

from src.models import (
    PortfolioTransaction,
    PortfolioTransactionType,
)
from src.repository import get_portfolio_transactions


_QUANTITY_TOLERANCE = 1e-12


@dataclass(frozen=True)
class PortfolioPosition:
    company_id: int
    currency: str

    quantity: float
    average_cost: float
    cost_basis: float

    realized_profit_loss: float

    total_buy_fees: float
    total_buy_taxes: float
    total_sell_fees: float
    total_sell_taxes: float


@dataclass(frozen=True)
class PortfolioSnapshot:
    as_of_date: date | None
    positions: tuple[PortfolioPosition, ...]


@dataclass
class _PositionState:
    company_id: int
    currency: str

    quantity: float = 0.0
    cost_basis: float = 0.0
    realized_profit_loss: float = 0.0

    total_buy_fees: float = 0.0
    total_buy_taxes: float = 0.0
    total_sell_fees: float = 0.0
    total_sell_taxes: float = 0.0


class PortfolioCalculationError(ValueError):
    pass


def build_portfolio_snapshot(
    connection: sqlite3.Connection,
    as_of_date: date | None = None,
) -> PortfolioSnapshot:
    transactions = get_portfolio_transactions(
        connection=connection,
        as_of_date=as_of_date,
    )

    return build_portfolio_snapshot_from_transactions(
        transactions=transactions,
        as_of_date=as_of_date,
    )


def build_portfolio_snapshot_from_transactions(
    transactions: tuple[PortfolioTransaction, ...],
    as_of_date: date | None = None,
) -> PortfolioSnapshot:
    states: dict[int, _PositionState] = {}

    ordered_transactions = sorted(
        transactions,
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.external_id,
        ),
    )

    for transaction in ordered_transactions:
        if (
            as_of_date is not None
            and transaction.transaction_date > as_of_date
        ):
            continue

        if transaction.transaction_type not in {
            PortfolioTransactionType.BUY,
            PortfolioTransactionType.SELL,
        }:
            continue

        company_id = transaction.company_id
        quantity = transaction.quantity
        price = transaction.price

        if (
            company_id is None
            or quantity is None
            or price is None
        ):
            raise PortfolioCalculationError(
                "buy/sell transaction is incomplete"
            )

        state = states.get(company_id)

        if state is None:
            state = _PositionState(
                company_id=company_id,
                currency=transaction.currency.upper(),
            )
            states[company_id] = state

        if (
            state.currency
            != transaction.currency.upper()
        ):
            raise PortfolioCalculationError(
                "all transactions for a position "
                "must use the same currency"
            )

        if (
            transaction.transaction_type
            == PortfolioTransactionType.BUY
        ):
            _apply_buy(
                state=state,
                transaction=transaction,
            )
        else:
            _apply_sell(
                state=state,
                transaction=transaction,
            )

    positions = tuple(
        _build_position(state)
        for state in sorted(
            states.values(),
            key=lambda item: item.company_id,
        )
    )

    return PortfolioSnapshot(
        as_of_date=as_of_date,
        positions=positions,
    )


def _apply_buy(
    state: _PositionState,
    transaction: PortfolioTransaction,
) -> None:
    quantity = transaction.quantity
    price = transaction.price

    if quantity is None or price is None:
        raise PortfolioCalculationError(
            "buy transaction is incomplete"
        )

    purchase_value = quantity * price

    acquisition_cost = (
        purchase_value
        + transaction.fee
        + transaction.tax
    )

    state.quantity += quantity
    state.cost_basis += acquisition_cost

    state.total_buy_fees += transaction.fee
    state.total_buy_taxes += transaction.tax


def _apply_sell(
    state: _PositionState,
    transaction: PortfolioTransaction,
) -> None:
    quantity = transaction.quantity
    price = transaction.price

    if quantity is None or price is None:
        raise PortfolioCalculationError(
            "sell transaction is incomplete"
        )

    if quantity > state.quantity + _QUANTITY_TOLERANCE:
        raise PortfolioCalculationError(
            "cannot sell more shares than owned"
        )

    if state.quantity <= _QUANTITY_TOLERANCE:
        raise PortfolioCalculationError(
            "cannot sell shares without a position"
        )

    average_cost = (
        state.cost_basis
        / state.quantity
    )

    disposed_cost_basis = (
        average_cost
        * quantity
    )

    net_sale_proceeds = (
        quantity * price
        - transaction.fee
        - transaction.tax
    )

    realized_profit_loss = (
        net_sale_proceeds
        - disposed_cost_basis
    )

    state.quantity -= quantity
    state.cost_basis -= disposed_cost_basis

    state.realized_profit_loss += (
        realized_profit_loss
    )

    state.total_sell_fees += transaction.fee
    state.total_sell_taxes += transaction.tax

    if abs(state.quantity) <= _QUANTITY_TOLERANCE:
        state.quantity = 0.0
        state.cost_basis = 0.0


def _build_position(
    state: _PositionState,
) -> PortfolioPosition:
    if state.quantity > _QUANTITY_TOLERANCE:
        average_cost = (
            state.cost_basis
            / state.quantity
        )
    else:
        average_cost = 0.0

    return PortfolioPosition(
        company_id=state.company_id,
        currency=state.currency,
        quantity=state.quantity,
        average_cost=average_cost,
        cost_basis=state.cost_basis,
        realized_profit_loss=(
            state.realized_profit_loss
        ),
        total_buy_fees=state.total_buy_fees,
        total_buy_taxes=state.total_buy_taxes,
        total_sell_fees=state.total_sell_fees,
        total_sell_taxes=state.total_sell_taxes,
    )