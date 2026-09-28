"""
ANOMALY DETECTION ENGINE
========================
Deterministic rule-based anomaly detection.
No AI — threshold-based only.

Returns AnomalyResult objects with:
- type
- severity (LOW / MEDIUM / HIGH)
- description (human-readable, factual language)
- affected entity
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.models.models import Transaction, TransactionType


@dataclass
class Anomaly:
    anomaly_type: str
    severity: str       # LOW | MEDIUM | HIGH
    description: str    # Factual, non-alarmist
    entity_id: Optional[int] = None
    entity_type: str = "TRANSACTION"
    detected_on: Optional[date] = None


# Thresholds — documented in RULES.md
LARGE_TRANSACTION_THRESHOLD = Decimal("50000")      # ₹50K single transaction
CATEGORY_SPIKE_RATIO = Decimal("1.5")               # 50% above 3-month average
INCOME_DROP_RATIO = Decimal("0.25")                 # 25% drop from 3-month average


def detect_large_transactions(
    transactions: list[Transaction],
    threshold: Decimal = LARGE_TRANSACTION_THRESHOLD,
) -> list[Anomaly]:
    anomalies = []
    for txn in transactions:
        if (
            abs(txn.amount) >= threshold
            and txn.transaction_type == TransactionType.EXPENSE
        ):
            anomalies.append(
                Anomaly(
                    anomaly_type="LARGE_TRANSACTION",
                    severity="MEDIUM",
                    description=(
                        f"Unusually large expense of ₹{abs(txn.amount):,.0f} "
                        f"on {txn.date} — '{txn.description}'. Review recommended."
                    ),
                    entity_id=txn.id,
                    entity_type="TRANSACTION",
                    detected_on=txn.date,
                )
            )
    return anomalies


def detect_duplicate_candidates(
    transactions: list[Transaction],
    window_days: int = 3,
    amount_tolerance: Decimal = Decimal("1"),  # ₹1
) -> list[Anomaly]:
    """
    Flag pairs that share: amount, description prefix, account — within window_days.
    Does NOT auto-delete. Returns review recommendations only.
    """
    anomalies = []
    seen: dict[tuple, list[int]] = {}

    for txn in sorted(transactions, key=lambda t: t.date):
        key = (txn.account_id, abs(txn.amount), txn.description[:30].strip().lower())
        bucket = seen.setdefault(key, [])

        for prev_id in bucket:
            # Find that transaction
            prev = next((t for t in transactions if t.id == prev_id), None)
            if prev and abs((txn.date - prev.date).days) <= window_days:
                anomalies.append(
                    Anomaly(
                        anomaly_type="POTENTIAL_DUPLICATE",
                        severity="LOW",
                        description=(
                            f"Possible duplicate: ₹{abs(txn.amount):,.0f} "
                            f"'{txn.description[:50]}' appears on {prev.date} and {txn.date}."
                        ),
                        entity_id=txn.id,
                        entity_type="TRANSACTION",
                        detected_on=txn.date,
                    )
                )

        bucket.append(txn.id)

    return anomalies


def detect_income_drop(
    transactions: list[Transaction],
    target_year: int,
    target_month: int,
) -> list[Anomaly]:
    """Detect significant income drop vs 3-month average."""
    from collections import defaultdict

    monthly_income: dict[tuple, Decimal] = defaultdict(Decimal)
    for txn in transactions:
        if txn.transaction_type == TransactionType.INCOME:
            ym = (txn.date.year, txn.date.month)
            monthly_income[ym] += abs(txn.amount)

    current = monthly_income.get((target_year, target_month), Decimal("0"))

    # Get prior 3 months
    all_months = sorted(monthly_income.keys())
    curr_idx = next((i for i, m in enumerate(all_months) if m == (target_year, target_month)), -1)
    prior = all_months[max(0, curr_idx - 3):curr_idx]
    if not prior:
        return []

    avg_income = sum(monthly_income[m] for m in prior) / len(prior)
    if avg_income > 0 and current < avg_income * (1 - INCOME_DROP_RATIO):
        return [
            Anomaly(
                anomaly_type="INCOME_DROP",
                severity="HIGH",
                description=(
                    f"Income this month (₹{current:,.0f}) is {((1 - current/avg_income)*100):.0f}% "
                    f"below the 3-month average (₹{avg_income:,.0f}). Review recommended."
                ),
                entity_type="CASHFLOW",
                detected_on=date(target_year, target_month, 1),
            )
        ]
    return []


def detect_all_anomalies(
    transactions: list[Transaction],
    target_year: int,
    target_month: int,
) -> list[Anomaly]:
    """Run all anomaly detectors and return combined results."""
    anomalies: list[Anomaly] = []
    anomalies.extend(detect_large_transactions(transactions))
    anomalies.extend(detect_duplicate_candidates(transactions))
    anomalies.extend(detect_income_drop(transactions, target_year, target_month))
    # Sort by severity
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(anomalies, key=lambda a: order.get(a.severity, 3))
