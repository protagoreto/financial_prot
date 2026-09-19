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

def expected_annual_return(
    eps_growth: float,
    dividend_yield: float,
    current_pe: float,
    terminal_pe: float,
    years: int = 5,
) -> float | None:
    if years <= 0:
        return None

    if current_pe <= 0 or terminal_pe <= 0:
        return None

    if eps_growth <= -1 or dividend_yield <= -1:
        return None

    growth_factor = (1 + eps_growth) ** years
    dividend_factor = (1 + dividend_yield) ** years
    multiple_factor = terminal_pe / current_pe

    total_factor = (
        growth_factor
        * dividend_factor
        * multiple_factor
    )

    return total_factor ** (1 / years) - 1


def required_eps_growth(
    target_return: float,
    dividend_yield: float,
    current_pe: float,
    terminal_pe: float,
    years: int = 5,
) -> float | None:
    if years <= 0:
        return None

    if current_pe <= 0 or terminal_pe <= 0:
        return None

    if target_return <= -1 or dividend_yield <= -1:
        return None

    return (
        (1 + target_return)
        / (1 + dividend_yield)
        * (current_pe / terminal_pe) ** (1 / years)
        - 1
    )


def required_purchase_pe(
    target_return: float,
    eps_growth: float,
    dividend_yield: float,
    terminal_pe: float,
    years: int = 5,
) -> float | None:
    if years <= 0:
        return None

    if terminal_pe <= 0:
        return None

    if (
        target_return <= -1
        or eps_growth <= -1
        or dividend_yield <= -1
    ):
        return None

    return terminal_pe * (
        (
            (1 + eps_growth)
            * (1 + dividend_yield)
        )
        / (1 + target_return)
    ) ** years


def required_purchase_price(
    forward_eps: float,
    target_return: float,
    eps_growth: float,
    dividend_yield: float,
    terminal_pe: float,
    years: int = 5,
) -> float | None:
    if forward_eps <= 0:
        return None

    purchase_pe = required_purchase_pe(
        target_return=target_return,
        eps_growth=eps_growth,
        dividend_yield=dividend_yield,
        terminal_pe=terminal_pe,
        years=years,
    )

    if purchase_pe is None:
        return None

    return forward_eps * purchase_pe