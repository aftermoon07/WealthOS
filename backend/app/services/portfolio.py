"""
PORTFOLIO ENGINE
================
Deterministic calculations — no AI, no rounding errors.

Methodology:
- Cost basis: Weighted-average cost (WAVG). See RULES.md.
- XIRR: Newton-Raphson on IRR equation using actual dated cash flows.
- CAGR: Applied when start/end value + duration are known.
- P&L = current market value - total cost basis.

References: RULES.md section "Portfolio Methodology"
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from app.models.models import InvestmentTransaction, InvestmentTxnType


# ─── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class Holding:
    security_id: int
    ticker: str
    name: str
    investment_type: str
    sector: Optional[str]
    quantity: Decimal
    average_cost: Decimal       # Weighted-average cost per unit
    total_cost: Decimal         # average_cost × quantity
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]     # quantity × current_price
    unrealized_pnl: Optional[Decimal]   # market_value - total_cost
    unrealized_pnl_pct: Optional[Decimal]
    price_source: str = "DEMO"
    price_date: Optional[date] = None


@dataclass
class PortfolioMetrics:
    total_invested: Decimal = Decimal("0")      # Sum of all buy costs
    total_market_value: Optional[Decimal] = None
    total_unrealized_pnl: Optional[Decimal] = None
    total_unrealized_pnl_pct: Optional[Decimal] = None
    total_realized_pnl: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")
    xirr: Optional[Decimal] = None
    xirr_confidence: str = "LOW"
    xirr_reason: str = ""
    cagr: Optional[Decimal] = None
    holdings: list[Holding] = field(default_factory=list)
    asset_allocation: dict[str, Decimal] = field(default_factory=dict)
    sector_allocation: dict[str, Decimal] = field(default_factory=dict)
    concentration: Optional[Decimal] = None   # Largest holding as % of portfolio
    top3_concentration: Optional[Decimal] = None


# ─── Cost Basis — Weighted Average ────────────────────────────────────────────


def calculate_holdings(
    investment_transactions: list[InvestmentTransaction],
    market_prices: dict[int, tuple[Decimal, str, date]],  # security_id → (price, source, date)
) -> list[Holding]:
    """
    Calculate current holdings using weighted-average cost basis.

    For each security:
      average_cost = Σ(quantity × price + fees) / Σ(quantity)  [across buys]
      On sell: reduce quantity; realized P&L tracked separately.

    market_prices: {security_id: (price, source, date)}
    """
    # {security_id: {"quantity": Decimal, "total_cost": Decimal}}
    position: dict[int, dict] = {}
    security_meta: dict[int, dict] = {}

    # Sort by date to process chronologically
    txns = sorted(investment_transactions, key=lambda t: t.date)

    for txn in txns:
        sid = txn.security_id
        if sid not in position:
            position[sid] = {"quantity": Decimal("0"), "total_cost": Decimal("0")}
            security_meta[sid] = {
                "ticker": txn.security.ticker,
                "name": txn.security.name,
                "investment_type": txn.security.investment_type.value,
                "sector": txn.security.sector,
            }

        pos = position[sid]
        cost_of_txn = txn.quantity * txn.price + txn.fees

        if txn.txn_type in (InvestmentTxnType.BUY, InvestmentTxnType.SIP):
            pos["quantity"] += txn.quantity
            pos["total_cost"] += cost_of_txn

        elif txn.txn_type == InvestmentTxnType.SELL:
            if pos["quantity"] > 0:
                # Proportionally reduce total cost (WAVG method)
                sell_ratio = min(txn.quantity / pos["quantity"], Decimal("1"))
                pos["total_cost"] -= pos["total_cost"] * sell_ratio
                pos["quantity"] -= txn.quantity
                pos["quantity"] = max(pos["quantity"], Decimal("0"))
                pos["total_cost"] = max(pos["total_cost"], Decimal("0"))

        elif txn.txn_type == InvestmentTxnType.BONUS:
            # Bonus shares: no cost, increase quantity, reduce average cost
            pos["quantity"] += txn.quantity

        elif txn.txn_type == InvestmentTxnType.SPLIT:
            # Stock split: multiply quantity by split ratio (stored in quantity field)
            # Split ratio = txn.quantity (e.g. 2.0 means 2:1 split)
            if pos["quantity"] > 0 and txn.quantity > 1:
                old_qty = pos["quantity"]
                pos["quantity"] = old_qty * txn.quantity
                # Total cost stays the same; per-unit cost drops

    holdings = []
    for sid, pos in position.items():
        if pos["quantity"] <= Decimal("0.0001"):
            continue  # Position closed / negligible

        meta = security_meta[sid]
        avg_cost = (
            (pos["total_cost"] / pos["quantity"]).quantize(Decimal("0.0001"))
            if pos["quantity"] > 0
            else Decimal("0")
        )

        price_info = market_prices.get(sid)
        current_price = price_info[0] if price_info else None
        price_source = price_info[1] if price_info else "UNKNOWN"
        price_date = price_info[2] if price_info else None

        market_value = (pos["quantity"] * current_price).quantize(Decimal("0.01")) if current_price else None
        unrealized_pnl = (market_value - pos["total_cost"]).quantize(Decimal("0.01")) if market_value is not None else None
        unrealized_pnl_pct = (
            (unrealized_pnl / pos["total_cost"] * 100).quantize(Decimal("0.01"))
            if unrealized_pnl is not None and pos["total_cost"] > 0
            else None
        )

        holdings.append(
            Holding(
                security_id=sid,
                ticker=meta["ticker"],
                name=meta["name"],
                investment_type=meta["investment_type"],
                sector=meta["sector"],
                quantity=pos["quantity"].quantize(Decimal("0.0001")),
                average_cost=avg_cost,
                total_cost=pos["total_cost"].quantize(Decimal("0.01")),
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                price_source=price_source,
                price_date=price_date,
            )
        )

    return holdings


# ─── Realized P&L ─────────────────────────────────────────────────────────────


def calculate_realized_pnl(
    investment_transactions: list[InvestmentTransaction],
) -> Decimal:
    """
    Realized P&L using weighted-average cost basis.
    On each sell: realized = (sell_price - avg_cost_at_time) × quantity - fees.
    """
    running: dict[int, dict] = {}  # security_id → {quantity, total_cost}
    total_realized = Decimal("0")

    for txn in sorted(investment_transactions, key=lambda t: t.date):
        sid = txn.security_id
        if sid not in running:
            running[sid] = {"quantity": Decimal("0"), "total_cost": Decimal("0")}

        r = running[sid]

        if txn.txn_type in (InvestmentTxnType.BUY, InvestmentTxnType.SIP):
            r["quantity"] += txn.quantity
            r["total_cost"] += txn.quantity * txn.price + txn.fees

        elif txn.txn_type == InvestmentTxnType.SELL and r["quantity"] > 0:
            avg_cost = r["total_cost"] / r["quantity"]
            qty_sold = min(txn.quantity, r["quantity"])
            realized = (txn.price - avg_cost) * qty_sold - txn.fees
            total_realized += realized

            # Update running position
            r["quantity"] -= qty_sold
            if r["quantity"] > 0:
                r["total_cost"] -= avg_cost * qty_sold
            else:
                r["total_cost"] = Decimal("0")

    return total_realized.quantize(Decimal("0.01"))


# ─── XIRR ─────────────────────────────────────────────────────────────────────


def calculate_xirr(
    cash_flows: list[tuple[date, Decimal]],
    tolerance: float = 1e-7,
    max_iterations: int = 200,
) -> Optional[float]:
    """
    Extended Internal Rate of Return (money-weighted return).

    cash_flows: list of (date, amount)
      - Investments OUT: negative amounts
      - Dividends/redemptions IN: positive amounts
      - Current portfolio value: positive amount at today's date

    Returns annualized rate as a float (e.g. 0.119 = 11.9%).
    Returns None if XIRR cannot be computed.

    Algorithm: Newton-Raphson. Reference: Microsoft Excel XIRR.
    """
    if len(cash_flows) < 2:
        return None

    dates = [cf[0] for cf in cash_flows]
    amounts = [float(cf[1]) for cf in cash_flows]

    # Validate: need at least one negative and one positive flow
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    # Day counts from first date
    t0 = dates[0]
    days = [(d - t0).days for d in dates]

    def npv(rate: float) -> float:
        return sum(a / ((1 + rate) ** (d / 365.0)) for a, d in zip(amounts, days))

    def dnpv(rate: float) -> float:
        return sum(
            -a * (d / 365.0) / ((1 + rate) ** (d / 365.0 + 1))
            for a, d in zip(amounts, days)
        )

    rate = 0.1  # initial guess: 10%
    for _ in range(max_iterations):
        f = npv(rate)
        df = dnpv(rate)
        if abs(df) < 1e-12:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < tolerance:
            return round(new_rate, 6)
        rate = new_rate

    return None  # did not converge


# ─── CAGR ─────────────────────────────────────────────────────────────────────


def calculate_cagr(
    start_value: Decimal,
    end_value: Decimal,
    years: float,
) -> Optional[Decimal]:
    """
    Compound Annual Growth Rate.
    CAGR = (end / start) ^ (1 / years) - 1

    Returns None if:
    - start_value <= 0
    - years <= 0
    - result is mathematically undefined
    """
    if start_value <= 0 or years <= 0:
        return None
    try:
        ratio = float(end_value / start_value)
        if ratio <= 0:
            return None
        cagr = ratio ** (1.0 / years) - 1.0
        return Decimal(str(round(cagr, 6)))
    except (ZeroDivisionError, OverflowError, ValueError):
        return None


# ─── Allocation ────────────────────────────────────────────────────────────────


def calculate_asset_allocation(holdings: list[Holding]) -> dict[str, Decimal]:
    """Returns {investment_type: weight_pct} for holdings with known market value."""
    total = sum(h.market_value for h in holdings if h.market_value is not None) or Decimal("0")
    if total == 0:
        return {}

    allocation: dict[str, Decimal] = {}
    for h in holdings:
        if h.market_value is None:
            continue
        key = h.investment_type
        allocation[key] = allocation.get(key, Decimal("0")) + h.market_value

    return {k: (v / total * 100).quantize(Decimal("0.01")) for k, v in allocation.items()}


def calculate_sector_allocation(holdings: list[Holding]) -> dict[str, Decimal]:
    """Returns {sector: weight_pct}. 'Unknown' for holdings without sector data."""
    total = sum(h.market_value for h in holdings if h.market_value is not None) or Decimal("0")
    if total == 0:
        return {}

    allocation: dict[str, Decimal] = {}
    for h in holdings:
        if h.market_value is None:
            continue
        sector = h.sector or "Unknown"
        allocation[sector] = allocation.get(sector, Decimal("0")) + h.market_value

    return {k: (v / total * 100).quantize(Decimal("0.01")) for k, v in allocation.items()}


def calculate_concentration(holdings: list[Holding]) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Returns (top1_pct, top3_pct) of portfolio market value.
    Returns (None, None) if no holdings have market values.
    """
    values = sorted(
        [h.market_value for h in holdings if h.market_value is not None],
        reverse=True,
    )
    if not values:
        return None, None

    total = sum(values)
    if total == 0:
        return None, None

    top1 = (values[0] / total * 100).quantize(Decimal("0.01"))
    top3 = (sum(values[:3]) / total * 100).quantize(Decimal("0.01"))
    return top1, top3


def assemble_portfolio_metrics(
    investment_transactions: list[InvestmentTransaction],
    market_prices: dict[int, tuple[Decimal, str, date]],
    today: date,
) -> PortfolioMetrics:
    """
    Full portfolio metrics assembly.
    Returns PortfolioMetrics with XIRR confidence assessment.
    """
    metrics = PortfolioMetrics()

    holdings = calculate_holdings(investment_transactions, market_prices)
    metrics.holdings = holdings

    # Invested capital = sum of all buy costs
    metrics.total_invested = sum(
        txn.quantity * txn.price + txn.fees
        for txn in investment_transactions
        if txn.txn_type in (InvestmentTxnType.BUY, InvestmentTxnType.SIP)
    )

    # Dividend income
    metrics.dividend_income = sum(
        txn.quantity * txn.price
        for txn in investment_transactions
        if txn.txn_type == InvestmentTxnType.DIVIDEND
    )

    # Market value
    valued = [h.market_value for h in holdings if h.market_value is not None]
    if valued:
        metrics.total_market_value = sum(valued)
        metrics.total_unrealized_pnl = metrics.total_market_value - sum(
            h.total_cost for h in holdings if h.market_value is not None
        )
        if metrics.total_invested > 0:
            metrics.total_unrealized_pnl_pct = (
                metrics.total_unrealized_pnl / metrics.total_invested * 100
            ).quantize(Decimal("0.01"))

    # Realized P&L
    metrics.total_realized_pnl = calculate_realized_pnl(investment_transactions)

    # Allocation
    metrics.asset_allocation = calculate_asset_allocation(holdings)
    metrics.sector_allocation = calculate_sector_allocation(holdings)
    top1, top3 = calculate_concentration(holdings)
    metrics.concentration = top1
    metrics.top3_concentration = top3

    # XIRR — build cash flows
    cash_flows: list[tuple[date, Decimal]] = []
    for txn in sorted(investment_transactions, key=lambda t: t.date):
        cost = txn.quantity * txn.price + txn.fees
        if txn.txn_type in (InvestmentTxnType.BUY, InvestmentTxnType.SIP):
            cash_flows.append((txn.date, -cost))  # money OUT
        elif txn.txn_type == InvestmentTxnType.SELL:
            proceeds = txn.quantity * txn.price - txn.fees
            cash_flows.append((txn.date, proceeds))  # money IN
        elif txn.txn_type == InvestmentTxnType.DIVIDEND:
            cash_flows.append((txn.date, txn.quantity * txn.price))

    if metrics.total_market_value is not None and metrics.total_market_value > 0:
        cash_flows.append((today, metrics.total_market_value))  # terminal value

    # Assess XIRR confidence
    missing_prices = len([h for h in holdings if h.current_price is None])
    months_of_data = len({(txn.date.year, txn.date.month) for txn in investment_transactions})

    if len(cash_flows) < 2:
        metrics.xirr_confidence = "LOW"
        metrics.xirr_reason = "Insufficient cash flows to compute XIRR."
    elif missing_prices > 0:
        metrics.xirr_confidence = "LOW"
        metrics.xirr_reason = f"{missing_prices} holding(s) have missing market prices."
    elif months_of_data < 3:
        metrics.xirr_confidence = "LOW"
        metrics.xirr_reason = "Less than 3 months of investment history."
    elif months_of_data < 6:
        metrics.xirr_confidence = "MEDIUM"
        metrics.xirr_reason = f"{months_of_data} months of investment history."
    else:
        metrics.xirr_confidence = "HIGH"
        metrics.xirr_reason = f"{months_of_data} months of complete investment transaction history."

    xirr_val = calculate_xirr(cash_flows)
    if xirr_val is not None:
        metrics.xirr = Decimal(str(round(xirr_val * 100, 2)))  # as percentage

    return metrics
