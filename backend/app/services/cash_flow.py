"""
DETERMINISTIC CASH-FLOW ENGINE
===============================
All calculations are pure Python — no AI involved.

Rules (documented in RULES.md):
- Transfers between own accounts do NOT count as expense or income.
- Investment purchases do NOT count as consumption.
- Credit card repayments (DEBT_PAYMENT) do NOT become another expense.
- Savings = Income - Expenses (transfers/investments excluded).
- Savings Rate = Savings / Income × 100.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from app.models.models import Transaction, TransactionType


EXCLUDE_FROM_CASHFLOW = {
    TransactionType.TRANSFER,
    TransactionType.INVESTMENT_BUY,
    TransactionType.DEBT_PAYMENT,
}


@dataclass
class CashFlowResult:
    income: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")
    investment_contributions: Decimal = Decimal("0")
    transfers: Decimal = Decimal("0")
    debt_payments: Decimal = Decimal("0")
    savings: Decimal = Decimal("0")
    savings_rate: Optional[Decimal] = None  # None if income == 0
    period_label: str = ""
    transaction_count: int = 0


def calculate_cash_flow(transactions: list[Transaction]) -> CashFlowResult:
    """
    Compute cash flow from a list of transactions.

    Only INCOME and EXPENSE transactions affect the savings calculation.
    TRANSFER, INVESTMENT_BUY, DEBT_PAYMENT are tracked separately.
    """
    result = CashFlowResult(transaction_count=len(transactions))

    for txn in transactions:
        amount = abs(txn.amount)
        t = txn.transaction_type

        if t == TransactionType.INCOME:
            result.income += amount
        elif t == TransactionType.EXPENSE:
            result.expenses += amount
        elif t == TransactionType.TRANSFER:
            result.transfers += amount
        elif t == TransactionType.INVESTMENT_BUY:
            result.investment_contributions += amount
        elif t == TransactionType.DEBT_PAYMENT:
            result.debt_payments += amount
        elif t == TransactionType.DIVIDEND:
            result.income += amount  # Dividends count as income
        elif t == TransactionType.INTEREST:
            result.expenses += amount  # Loan interest = expense
        elif t == TransactionType.FEE:
            result.expenses += amount
        elif t == TransactionType.REFUND:
            result.expenses -= amount  # Refund reduces expenses
        elif t == TransactionType.INVESTMENT_SELL:
            pass  # Proceeds go back to cash — not income in cash-flow context

    result.savings = result.income - result.expenses
    if result.income > 0:
        result.savings_rate = (result.savings / result.income * 100).quantize(
            Decimal("0.01")
        )

    return result


@dataclass
class MonthlyComparison:
    current: CashFlowResult
    previous: CashFlowResult
    income_change: Decimal = field(init=False)
    income_change_pct: Optional[Decimal] = field(init=False)
    expense_change: Decimal = field(init=False)
    expense_change_pct: Optional[Decimal] = field(init=False)
    savings_change: Decimal = field(init=False)

    def __post_init__(self):
        self.income_change = self.current.income - self.previous.income
        self.expense_change = self.current.expenses - self.previous.expenses
        self.savings_change = self.current.savings - self.previous.savings

        if self.previous.income > 0:
            self.income_change_pct = (
                self.income_change / self.previous.income * 100
            ).quantize(Decimal("0.1"))
        else:
            self.income_change_pct = None

        if self.previous.expenses > 0:
            self.expense_change_pct = (
                self.expense_change / self.previous.expenses * 100
            ).quantize(Decimal("0.1"))
        else:
            self.expense_change_pct = None
