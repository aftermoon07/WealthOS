"""
SPENDING ANALYTICS ENGINE
==========================
Deterministic spending analysis — no AI.

Calculates category breakdowns, month-over-month changes,
rolling averages, anomalies, and recurring transactions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from app.models.models import Transaction, TransactionType


@dataclass
class CategorySpend:
    category: str
    current_month: Decimal
    avg_3m: Optional[Decimal]
    avg_6m: Optional[Decimal]
    avg_12m: Optional[Decimal]
    mom_change: Optional[Decimal]       # vs previous month
    mom_change_pct: Optional[Decimal]
    is_anomaly: bool = False
    anomaly_reason: str = ""


@dataclass
class SpendingAnalysis:
    period_month: int
    period_year: int
    total_spending: Decimal
    categories: list[CategorySpend]
    largest_transactions: list[dict]
    recurring_merchants: list[dict]
    spending_anomalies: list[dict]


def _is_expense(txn: Transaction) -> bool:
    return txn.transaction_type in (
        TransactionType.EXPENSE,
        TransactionType.FEE,
        TransactionType.INTEREST,
    )


def analyze_spending(
    transactions: list[Transaction],
    target_year: int,
    target_month: int,
) -> SpendingAnalysis:
    """
    Full spending analysis for a given month.
    transactions: all transactions (up to 12 months recommended).
    """
    # Group by (year, month, category)
    monthly_by_cat: dict[tuple, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for txn in transactions:
        if not _is_expense(txn):
            continue
        ym = (txn.date.year, txn.date.month)
        cat = (
            txn.category_rel.name
            if txn.category_rel
            else "Uncategorized"
        )
        monthly_by_cat[ym][cat] += abs(txn.amount)

    current_key = (target_year, target_month)
    current_spend = monthly_by_cat.get(current_key, {})
    total_spending = sum(current_spend.values(), Decimal("0"))

    # Build prior months list (up to 12)
    all_months = sorted(monthly_by_cat.keys())

    def months_before(ym: tuple, n: int) -> list[tuple]:
        idx = all_months.index(ym) if ym in all_months else -1
        if idx < 0:
            return [m for m in all_months[-n:]]
        return all_months[max(0, idx - n):idx]

    prior_1 = months_before(current_key, 1)
    prior_3 = months_before(current_key, 3)
    prior_6 = months_before(current_key, 6)
    prior_12 = months_before(current_key, 12)

    prev_month_key = prior_1[-1] if prior_1 else None

    all_cats = set(current_spend.keys())
    for ym_data in monthly_by_cat.values():
        all_cats.update(ym_data.keys())

    categories = []
    for cat in sorted(all_cats):
        curr = current_spend.get(cat, Decimal("0"))

        def avg_for(months_list):
            vals = [monthly_by_cat[m].get(cat, Decimal("0")) for m in months_list]
            if not vals:
                return None
            return (sum(vals) / len(vals)).quantize(Decimal("0.01"))

        avg3 = avg_for(prior_3)
        avg6 = avg_for(prior_6)
        avg12 = avg_for(prior_12)

        prev = monthly_by_cat.get(prev_month_key, {}).get(cat, Decimal("0")) if prev_month_key else None
        mom_change = (curr - prev) if prev is not None else None
        mom_pct = (
            (mom_change / prev * 100).quantize(Decimal("0.1"))
            if mom_change is not None and prev and prev > 0
            else None
        )

        # Anomaly: current > 1.5× the 3-month average
        is_anomaly = False
        anomaly_reason = ""
        if avg3 and avg3 > 0 and curr > avg3 * Decimal("1.5"):
            is_anomaly = True
            anomaly_reason = f"Spending is {((curr/avg3 - 1)*100):.0f}% above 3-month average"

        categories.append(CategorySpend(
            category=cat,
            current_month=curr,
            avg_3m=avg3,
            avg_6m=avg6,
            avg_12m=avg12,
            mom_change=mom_change,
            mom_change_pct=mom_pct,
            is_anomaly=is_anomaly,
            anomaly_reason=anomaly_reason,
        ))

    # Sort by current spend descending
    categories.sort(key=lambda c: c.current_month, reverse=True)

    # Largest transactions this month
    current_txns = [
        t for t in transactions
        if t.date.year == target_year and t.date.month == target_month and _is_expense(t)
    ]
    largest = sorted(current_txns, key=lambda t: abs(t.amount), reverse=True)[:10]
    largest_out = [
        {
            "id": t.id,
            "date": str(t.date),
            "description": t.description,
            "merchant": t.merchant,
            "amount": str(abs(t.amount)),
            "category": t.category_rel.name if t.category_rel else "Uncategorized",
        }
        for t in largest
    ]

    # Recurring merchants (appear ≥2 times in last 3 months)
    merchant_counts: dict[str, int] = defaultdict(int)
    for ym in prior_3 + [current_key]:
        for t in transactions:
            if (t.date.year, t.date.month) == ym and _is_expense(t) and t.merchant:
                merchant_counts[t.merchant] += 1

    recurring = [
        {"merchant": m, "occurrences": c}
        for m, c in sorted(merchant_counts.items(), key=lambda x: -x[1])
        if c >= 2
    ]

    # Spending anomalies
    anomalies = [
        {"category": c.category, "amount": str(c.current_month), "reason": c.anomaly_reason}
        for c in categories
        if c.is_anomaly
    ]

    return SpendingAnalysis(
        period_month=target_month,
        period_year=target_year,
        total_spending=total_spending,
        categories=categories,
        largest_transactions=largest_out,
        recurring_merchants=recurring,
        spending_anomalies=anomalies,
    )
