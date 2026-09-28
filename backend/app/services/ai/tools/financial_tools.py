"""
AI TOOL LAYER
=============
Controlled tools that the AI agent may call.
The LLM has NO direct database access.

Each tool retrieves the minimum data needed.
Tools return structured dicts — not raw ORM objects.

Architecture:
  AI Agent → calls tool → tool queries DB → runs deterministic engine
           → returns structured data → AI interprets

See: AI.md for full documentation.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.models.models import (
    Account, Transaction, InvestmentTransaction, Security,
    MarketPrice, Goal, NetWorthSnapshot, TransactionType,
    AccountType, InvestmentTxnType,
)
from app.services.cash_flow import calculate_cash_flow
from app.services.net_worth import calculate_net_worth, calculate_emergency_fund_coverage
from app.services.portfolio import assemble_portfolio_metrics
from app.services.spending import analyze_spending
from app.services.anomalies import detect_all_anomalies


def _d(val) -> Optional[str]:
    """Safely convert Decimal/None to string for JSON serialization."""
    if val is None:
        return None
    return str(round(val, 2))


async def get_financial_summary(
    db: AsyncSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """
    Top-level financial summary for the AI.
    Returns monthly income, expenses, savings, net worth, portfolio value.
    """
    today = date.today()
    year = year or today.year
    month = month or today.month

    # Transactions this month
    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.date >= date(year, month, 1),
                Transaction.date < date(year, month + 1 if month < 12 else 1, 1)
                if month < 12 else date(year + 1, 1, 1),
            )
        ).options(selectinload(Transaction.account), selectinload(Transaction.category_rel))
    )
    txns = result.scalars().all()

    cf = calculate_cash_flow(list(txns))

    # Accounts
    acc_result = await db.execute(select(Account).where(Account.is_active == True))
    accounts = acc_result.scalars().all()

    # Portfolio (simplified — market value from latest prices)
    portfolio_value = await _get_portfolio_value(db)

    nw = calculate_net_worth(list(accounts), portfolio_value)

    return {
        "period": f"{year}-{month:02d}",
        "monthly_income": _d(cf.income),
        "monthly_expenses": _d(cf.expenses),
        "monthly_savings": _d(cf.savings),
        "savings_rate": _d(cf.savings_rate),
        "investment_contributions": _d(cf.investment_contributions),
        "net_worth": _d(nw.net_worth),
        "total_assets": _d(nw.total_assets),
        "total_liabilities": _d(nw.total_liabilities),
        "cash_and_bank": _d(nw.cash_and_bank),
        "portfolio_value": _d(portfolio_value),
        "liquid_savings": _d(nw.liquid_savings),
        "data_source": "DETERMINISTIC_ENGINE",
    }


async def get_spending_analysis(
    db: AsyncSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Spending breakdown by category for a given month."""
    today = date.today()
    year = year or today.year
    month = month or today.month

    # Get 12 months of transactions for rolling averages
    from_date = date(year - 1, month, 1)
    result = await db.execute(
        select(Transaction).where(Transaction.date >= from_date)
        .options(selectinload(Transaction.category_rel))
    )
    txns = result.scalars().all()

    analysis = analyze_spending(list(txns), year, month)

    return {
        "period": f"{year}-{month:02d}",
        "total_spending": _d(analysis.total_spending),
        "categories": [
            {
                "category": c.category,
                "current_month": _d(c.current_month),
                "avg_3m": _d(c.avg_3m),
                "mom_change_pct": _d(c.mom_change_pct),
                "is_anomaly": c.is_anomaly,
                "anomaly_reason": c.anomaly_reason,
            }
            for c in analysis.categories
            if c.current_month > 0
        ],
        "largest_transactions": analysis.largest_transactions[:5],
        "spending_anomalies": analysis.spending_anomalies,
    }


async def get_portfolio_summary(db: AsyncSession) -> dict:
    """Portfolio metrics for the AI — no raw data, only aggregates."""
    today = date.today()

    inv_result = await db.execute(
        select(InvestmentTransaction).options(selectinload(InvestmentTransaction.security))
    )
    inv_txns = inv_result.scalars().all()

    prices = await _load_market_prices(db)
    metrics = assemble_portfolio_metrics(list(inv_txns), prices, today)

    return {
        "total_invested": _d(metrics.total_invested),
        "portfolio_value": _d(metrics.total_market_value),
        "unrealized_pnl": _d(metrics.total_unrealized_pnl),
        "unrealized_pnl_pct": _d(metrics.total_unrealized_pnl_pct),
        "realized_pnl": _d(metrics.total_realized_pnl),
        "dividend_income": _d(metrics.dividend_income),
        "xirr": _d(metrics.xirr),
        "xirr_confidence": metrics.xirr_confidence,
        "xirr_reason": metrics.xirr_reason,
        "asset_allocation": {k: _d(v) for k, v in metrics.asset_allocation.items()},
        "largest_holding_weight": _d(metrics.concentration),
        "top3_holding_weight": _d(metrics.top3_concentration),
        "holding_count": len(metrics.holdings),
    }


async def get_holdings(db: AsyncSession) -> dict:
    """Current holdings for the AI."""
    today = date.today()

    inv_result = await db.execute(
        select(InvestmentTransaction).options(selectinload(InvestmentTransaction.security))
    )
    inv_txns = inv_result.scalars().all()

    prices = await _load_market_prices(db)
    metrics = assemble_portfolio_metrics(list(inv_txns), prices, today)

    return {
        "holdings": [
            {
                "ticker": h.ticker,
                "name": h.name,
                "investment_type": h.investment_type,
                "sector": h.sector,
                "quantity": _d(h.quantity),
                "average_cost": _d(h.average_cost),
                "current_price": _d(h.current_price),
                "market_value": _d(h.market_value),
                "unrealized_pnl": _d(h.unrealized_pnl),
                "unrealized_pnl_pct": _d(h.unrealized_pnl_pct),
                "price_source": h.price_source,
            }
            for h in sorted(
                metrics.holdings,
                key=lambda h: float(h.market_value or 0),
                reverse=True,
            )
        ]
    }


async def get_asset_allocation(db: AsyncSession) -> dict:
    """Asset allocation + sector breakdown for the AI."""
    today = date.today()
    inv_result = await db.execute(
        select(InvestmentTransaction).options(selectinload(InvestmentTransaction.security))
    )
    inv_txns = inv_result.scalars().all()

    prices = await _load_market_prices(db)
    metrics = assemble_portfolio_metrics(list(inv_txns), prices, today)

    return {
        "asset_allocation": {k: _d(v) for k, v in metrics.asset_allocation.items()},
        "sector_allocation": {k: _d(v) for k, v in metrics.sector_allocation.items()},
        "largest_holding_pct": _d(metrics.concentration),
        "top3_holdings_pct": _d(metrics.top3_concentration),
    }


async def get_portfolio_risk(db: AsyncSession) -> dict:
    """Risk dimensions for the AI — explainable, not a single arbitrary score."""
    today = date.today()
    inv_result = await db.execute(
        select(InvestmentTransaction).options(selectinload(InvestmentTransaction.security))
    )
    inv_txns = inv_result.scalars().all()

    prices = await _load_market_prices(db)
    metrics = assemble_portfolio_metrics(list(inv_txns), prices, today)

    risks = []

    # Concentration risk
    if metrics.concentration is not None:
        if metrics.concentration > 30:
            risks.append({
                "dimension": "Concentration",
                "level": "HIGH",
                "metric": f"{_d(metrics.concentration)}%",
                "reason": f"Your largest holding represents {_d(metrics.concentration)}% of portfolio value.",
            })
        elif metrics.concentration > 20:
            risks.append({
                "dimension": "Concentration",
                "level": "MEDIUM",
                "metric": f"{_d(metrics.concentration)}%",
                "reason": f"Your largest holding is {_d(metrics.concentration)}% of portfolio.",
            })

    # Missing prices
    missing_price_count = len([h for h in metrics.holdings if h.current_price is None])
    if missing_price_count > 0:
        risks.append({
            "dimension": "Data Quality",
            "level": "MEDIUM",
            "metric": f"{missing_price_count} holdings",
            "reason": f"{missing_price_count} holding(s) have no current market price. Portfolio value may be understated.",
        })

    # XIRR confidence
    if metrics.xirr_confidence == "LOW":
        risks.append({
            "dimension": "Return Measurement",
            "level": "LOW",
            "metric": "Low confidence",
            "reason": metrics.xirr_reason,
        })

    return {
        "risk_dimensions": risks,
        "xirr_confidence": metrics.xirr_confidence,
        "data_completeness": "PARTIAL" if missing_price_count > 0 else "COMPLETE",
    }


async def get_anomalies(
    db: AsyncSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Detected anomalies for the AI."""
    today = date.today()
    year = year or today.year
    month = month or today.month

    from_date = date(year - 1, month, 1)
    result = await db.execute(
        select(Transaction).where(Transaction.date >= from_date)
    )
    txns = result.scalars().all()

    anomalies = detect_all_anomalies(list(txns), year, month)

    return {
        "anomaly_count": len(anomalies),
        "anomalies": [
            {
                "type": a.anomaly_type,
                "severity": a.severity,
                "description": a.description,
                "date": str(a.detected_on) if a.detected_on else None,
            }
            for a in anomalies
        ],
    }


async def get_goal_progress(db: AsyncSession) -> dict:
    """Goal progress for the AI."""
    result = await db.execute(select(Goal).where(Goal.is_active == True))
    goals = result.scalars().all()

    output = []
    for g in goals:
        pct = (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else Decimal("0")
        remaining = g.target_amount - g.current_amount

        # Project if we have monthly contribution and target date
        projected = None
        if g.monthly_contribution and g.monthly_contribution > 0 and g.target_date:
            months_left = (
                (g.target_date.year - date.today().year) * 12
                + g.target_date.month - date.today().month
            )
            if months_left > 0:
                projected = g.current_amount + g.monthly_contribution * months_left

        output.append({
            "name": g.name,
            "type": g.goal_type.value,
            "target": _d(g.target_amount),
            "current": _d(g.current_amount),
            "progress_pct": _d(pct),
            "remaining": _d(remaining),
            "target_date": str(g.target_date) if g.target_date else None,
            "monthly_contribution": _d(g.monthly_contribution),
            "projected_value": _d(projected),
        })

    return {"goals": output, "goal_count": len(output)}


async def get_monthly_comparison(
    db: AsyncSession,
    year: int,
    month: int,
) -> dict:
    """Compare current month to previous month."""
    # Current month
    curr_summary = await get_financial_summary(db, year, month)

    # Previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_summary = await get_financial_summary(db, prev_year, prev_month)

    def _change(curr_str, prev_str):
        if curr_str is None or prev_str is None:
            return None
        c, p = Decimal(curr_str), Decimal(prev_str)
        if p == 0:
            return None
        return _d((c - p) / abs(p) * 100)

    return {
        "current": curr_summary,
        "previous": prev_summary,
        "income_change_pct": _change(curr_summary["monthly_income"], prev_summary["monthly_income"]),
        "expense_change_pct": _change(curr_summary["monthly_expenses"], prev_summary["monthly_expenses"]),
        "savings_change_pct": _change(curr_summary["monthly_savings"], prev_summary["monthly_savings"]),
        "net_worth_change_pct": _change(curr_summary["net_worth"], prev_summary["net_worth"]),
    }


async def get_net_worth_history(db: AsyncSession) -> dict:
    """Historical net worth snapshots."""
    result = await db.execute(
        select(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()

    return {
        "history": [
            {
                "date": str(s.snapshot_date),
                "net_worth": _d(s.net_worth),
                "total_assets": _d(s.total_assets),
                "total_liabilities": _d(s.total_liabilities),
            }
            for s in snapshots
        ]
    }


# ─── Private Helpers ───────────────────────────────────────────────────────────

async def _load_market_prices(db: AsyncSession) -> dict[int, tuple[Decimal, str, date]]:
    """Load latest price per security."""
    result = await db.execute(select(MarketPrice).order_by(MarketPrice.price_date.desc()))
    prices = result.scalars().all()

    latest: dict[int, tuple[Decimal, str, date]] = {}
    for p in prices:
        if p.security_id not in latest:
            latest[p.security_id] = (p.price, p.source.value, p.price_date)
    return latest


async def _get_portfolio_value(db: AsyncSession) -> Decimal:
    """Fast portfolio value calculation."""
    inv_result = await db.execute(
        select(InvestmentTransaction).options(selectinload(InvestmentTransaction.security))
    )
    inv_txns = inv_result.scalars().all()

    prices = await _load_market_prices(db)
    today = date.today()
    metrics = assemble_portfolio_metrics(list(inv_txns), prices, today)
    return metrics.total_market_value or Decimal("0")
