def price_to_earnings(
    price: float,
    eps: float,
) -> float | None:
    if price <= 0 or eps <= 0:
        return None

    return price / eps


def earnings_yield(
    price: float,
    eps: float,
) -> float | None:
    if price <= 0 or eps <= 0:
        return None

    return eps / price


def dividend_yield(
    price: float,
    dividend_per_share: float,
) -> float | None:
    if price <= 0 or dividend_per_share < 0:
        return None

    return dividend_per_share / price


def free_cash_flow_yield(
    market_cap: float,
    free_cash_flow: float,
) -> float | None:
    if market_cap <= 0:
        return None

    return free_cash_flow / market_cap


def net_debt_to_ebitda(
    net_debt: float,
    ebitda: float,
) -> float | None:
    if ebitda <= 0:
        return None

    return net_debt / ebitda