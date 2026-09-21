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
    	key=lambda transaction: transaction.transaction_date,
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


@dataclass(frozen=True)
class ValuedPortfolioPosition:
    company_id: int
    currency: str

    quantity: float
    average_cost: float
    cost_basis: float
    realized_profit_loss: float

    price: float
    price_date: date

    market_value: float
    unrealized_profit_loss: float
    unrealized_return: float | None

    weight: float | None


@dataclass(frozen=True)
class PortfolioCurrencySummary:
    currency: str
    positions_market_value: float
    cash: float
    total_value: float


@dataclass(frozen=True)
class ValuedPortfolioSnapshot:
    as_of_date: date
    positions: tuple[ValuedPortfolioPosition, ...]
    currency_summaries: tuple[PortfolioCurrencySummary, ...]


def build_valued_portfolio_snapshot(
    connection: sqlite3.Connection,
    as_of_date: date,
) -> ValuedPortfolioSnapshot:
    from src.repository import get_price_on_or_before

    portfolio_snapshot = build_portfolio_snapshot(
        connection=connection,
        as_of_date=as_of_date,
    )

    transactions = get_portfolio_transactions(
        connection=connection,
        as_of_date=as_of_date,
    )

    cash_by_currency = _calculate_cash_by_currency(
        transactions=transactions,
    )

    position_data: list[dict] = []
    market_value_by_currency: dict[str, float] = {}

    for position in portfolio_snapshot.positions:
        if position.quantity <= _QUANTITY_TOLERANCE:
            continue

        price_record = get_price_on_or_before(
            connection=connection,
            company_id=position.company_id,
            as_of_date=as_of_date,
        )

        if price_record is None:
            raise PortfolioCalculationError(
                "missing price on or before "
                f"{as_of_date.isoformat()} "
                f"for company_id={position.company_id}"
            )

        price_currency = (
            price_record.currency.upper()
            if price_record.currency is not None
            else None
        )

        if price_currency is None:
            raise PortfolioCalculationError(
                "price currency is required "
                f"for company_id={position.company_id}"
            )

        if price_currency != position.currency:
            raise PortfolioCalculationError(
                "position currency and price currency "
                "must match"
            )

        market_value = (
            position.quantity
            * price_record.close
        )

        unrealized_profit_loss = (
            market_value
            - position.cost_basis
        )

        if position.cost_basis > 0:
            unrealized_return = (
                unrealized_profit_loss
                / position.cost_basis
            )
        else:
            unrealized_return = None

        market_value_by_currency[position.currency] = (
            market_value_by_currency.get(
                position.currency,
                0.0,
            )
            + market_value
        )

        position_data.append(
            {
                "position": position,
                "price": price_record.close,
                "price_date": price_record.price_date,
                "market_value": market_value,
                "unrealized_profit_loss": (
                    unrealized_profit_loss
                ),
                "unrealized_return": unrealized_return,
            }
        )

    currencies = (
        set(market_value_by_currency)
        | set(cash_by_currency)
    )

    total_value_by_currency = {
        currency: (
            market_value_by_currency.get(
                currency,
                0.0,
            )
            + cash_by_currency.get(
                currency,
                0.0,
            )
        )
        for currency in currencies
    }

    valued_positions = tuple(
        ValuedPortfolioPosition(
            company_id=item["position"].company_id,
            currency=item["position"].currency,
            quantity=item["position"].quantity,
            average_cost=item["position"].average_cost,
            cost_basis=item["position"].cost_basis,
            realized_profit_loss=(
                item["position"].realized_profit_loss
            ),
            price=item["price"],
            price_date=item["price_date"],
            market_value=item["market_value"],
            unrealized_profit_loss=(
                item["unrealized_profit_loss"]
            ),
            unrealized_return=item["unrealized_return"],
            weight=_calculate_weight(
                market_value=item["market_value"],
                total_value=total_value_by_currency[
                    item["position"].currency
                ],
            ),
        )
        for item in position_data
    )

    currency_summaries = tuple(
        PortfolioCurrencySummary(
            currency=currency,
            positions_market_value=(
                market_value_by_currency.get(
                    currency,
                    0.0,
                )
            ),
            cash=cash_by_currency.get(
                currency,
                0.0,
            ),
            total_value=total_value_by_currency[
                currency
            ],
        )
        for currency in sorted(currencies)
    )

    return ValuedPortfolioSnapshot(
        as_of_date=as_of_date,
        positions=valued_positions,
        currency_summaries=currency_summaries,
    )


def _calculate_cash_by_currency(
    transactions: tuple[PortfolioTransaction, ...],
) -> dict[str, float]:
    cash_by_currency: dict[str, float] = {}

    for transaction in transactions:
        currency = transaction.currency.upper()

        cash_effect = _transaction_cash_effect(
            transaction=transaction,
        )

        cash_by_currency[currency] = (
            cash_by_currency.get(currency, 0.0)
            + cash_effect
        )

    return cash_by_currency


def _transaction_cash_effect(
    transaction: PortfolioTransaction,
) -> float:
    transaction_type = transaction.transaction_type

    if transaction_type == PortfolioTransactionType.BUY:
        if (
            transaction.quantity is None
            or transaction.price is None
        ):
            raise PortfolioCalculationError(
                "buy transaction is incomplete"
            )

        return -(
            transaction.quantity
            * transaction.price
            + transaction.fee
            + transaction.tax
        )

    if transaction_type == PortfolioTransactionType.SELL:
        if (
            transaction.quantity is None
            or transaction.price is None
        ):
            raise PortfolioCalculationError(
                "sell transaction is incomplete"
            )

        return (
            transaction.quantity
            * transaction.price
            - transaction.fee
            - transaction.tax
        )

    if transaction_type == PortfolioTransactionType.DIVIDEND:
        if transaction.amount is None:
            raise PortfolioCalculationError(
                "dividend transaction is incomplete"
            )

        return (
            transaction.amount
            - transaction.fee
            - transaction.tax
        )

    if transaction_type == PortfolioTransactionType.FEE:
        if transaction.amount is None:
            raise PortfolioCalculationError(
                "fee transaction is incomplete"
            )

        return -transaction.amount

    if transaction_type == PortfolioTransactionType.TAX:
        if transaction.amount is None:
            raise PortfolioCalculationError(
                "tax transaction is incomplete"
            )

        return -transaction.amount

    if transaction_type == PortfolioTransactionType.CASH:
        if transaction.amount is None:
            raise PortfolioCalculationError(
                "cash transaction is incomplete"
            )

        return transaction.amount

    raise PortfolioCalculationError(
        f"unsupported transaction type: {transaction_type}"
    )


def _calculate_weight(
    market_value: float,
    total_value: float,
) -> float | None:
    if total_value <= 0:
        return None

    return market_value / total_value

@dataclass(frozen=True)
class PortfolioIncomeSummary:
    currency: str

    gross_dividends: float
    dividend_fees: float
    dividend_taxes: float
    net_dividends: float

    realized_profit_loss: float
    unrealized_profit_loss: float

    economic_profit_loss: float


@dataclass(frozen=True)
class PortfolioPerformanceSnapshot:
    as_of_date: date
    income_summaries: tuple[PortfolioIncomeSummary, ...]


def build_portfolio_performance_snapshot(
    connection: sqlite3.Connection,
    as_of_date: date,
) -> PortfolioPerformanceSnapshot:
    valued_snapshot = build_valued_portfolio_snapshot(
        connection=connection,
        as_of_date=as_of_date,
    )

    transactions = get_portfolio_transactions(
        connection=connection,
        as_of_date=as_of_date,
    )

    dividend_data = _calculate_dividends_by_currency(
        transactions=transactions,
    )

    realized_by_currency: dict[str, float] = {}
    unrealized_by_currency: dict[str, float] = {}

    portfolio_snapshot = build_portfolio_snapshot(
        connection=connection,
        as_of_date=as_of_date,
    )

    for position in portfolio_snapshot.positions:
        realized_by_currency[position.currency] = (
            realized_by_currency.get(
                position.currency,
                0.0,
            )
            + position.realized_profit_loss
        )

    for position in valued_snapshot.positions:
        unrealized_by_currency[position.currency] = (
            unrealized_by_currency.get(
                position.currency,
                0.0,
            )
            + position.unrealized_profit_loss
        )

    currencies = (
        set(dividend_data)
        | set(realized_by_currency)
        | set(unrealized_by_currency)
    )

    summaries = tuple(
        _build_income_summary(
            currency=currency,
            dividend_data=dividend_data,
            realized_by_currency=realized_by_currency,
            unrealized_by_currency=unrealized_by_currency,
        )
        for currency in sorted(currencies)
    )

    return PortfolioPerformanceSnapshot(
        as_of_date=as_of_date,
        income_summaries=summaries,
    )


def _calculate_dividends_by_currency(
    transactions: tuple[PortfolioTransaction, ...],
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}

    for transaction in transactions:
        if (
            transaction.transaction_type
            != PortfolioTransactionType.DIVIDEND
        ):
            continue

        if transaction.amount is None:
            raise PortfolioCalculationError(
                "dividend transaction is incomplete"
            )

        currency = transaction.currency.upper()

        data = result.setdefault(
            currency,
            {
                "gross": 0.0,
                "fees": 0.0,
                "taxes": 0.0,
            },
        )

        data["gross"] += transaction.amount
        data["fees"] += transaction.fee
        data["taxes"] += transaction.tax

    return result


def _build_income_summary(
    currency: str,
    dividend_data: dict[str, dict[str, float]],
    realized_by_currency: dict[str, float],
    unrealized_by_currency: dict[str, float],
) -> PortfolioIncomeSummary:
    dividends = dividend_data.get(
        currency,
        {
            "gross": 0.0,
            "fees": 0.0,
            "taxes": 0.0,
        },
    )

    gross_dividends = dividends["gross"]
    dividend_fees = dividends["fees"]
    dividend_taxes = dividends["taxes"]

    net_dividends = (
        gross_dividends
        - dividend_fees
        - dividend_taxes
    )

    realized_profit_loss = realized_by_currency.get(
        currency,
        0.0,
    )

    unrealized_profit_loss = unrealized_by_currency.get(
        currency,
        0.0,
    )

    economic_profit_loss = (
        realized_profit_loss
        + unrealized_profit_loss
        + net_dividends
    )

    return PortfolioIncomeSummary(
        currency=currency,
        gross_dividends=gross_dividends,
        dividend_fees=dividend_fees,
        dividend_taxes=dividend_taxes,
        net_dividends=net_dividends,
        realized_profit_loss=realized_profit_loss,
        unrealized_profit_loss=unrealized_profit_loss,
        economic_profit_loss=economic_profit_loss,
    )