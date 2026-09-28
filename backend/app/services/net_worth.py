"""
NET WORTH ENGINE
================
Net Worth = Total Assets - Total Liabilities

Assets include: cash/bank balances, investment portfolio value.
Liabilities include: loan outstanding, credit card outstanding.

IMPORTANT: Stocks, mutual funds, illiquid real estate are NOT
counted as liquid emergency savings.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.models.models import Account, AccountType


@dataclass
class NetWorthResult:
    # Assets
    cash_and_bank: Decimal = Decimal("0")
    investment_value: Decimal = Decimal("0")
    other_assets: Decimal = Decimal("0")
    total_assets: Decimal = Decimal("0")

    # Liabilities
    loan_outstanding: Decimal = Decimal("0")
    credit_card_outstanding: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")

    net_worth: Decimal = Decimal("0")

    # Liquidity
    liquid_savings: Decimal = Decimal("0")  # Only cash/savings accounts


def calculate_net_worth(
    accounts: list[Account],
    portfolio_value: Decimal = Decimal("0"),
) -> NetWorthResult:
    """
    Calculate net worth from accounts + portfolio market value.

    portfolio_value: current market value of all investment holdings
    (comes from the portfolio engine — do not recalculate here).
    """
    result = NetWorthResult()

    for acc in accounts:
        if not acc.is_active:
            continue

        t = acc.account_type

        if t in (AccountType.CHECKING, AccountType.SAVINGS):
            # Balance is tracked via transactions — use outstanding if set
            # For demo mode, we use outstanding_balance as the current balance
            balance = acc.outstanding_balance or Decimal("0")
            result.cash_and_bank += balance
            result.liquid_savings += balance  # these are liquid

        elif t == AccountType.CREDIT_CARD:
            outstanding = acc.outstanding_balance or Decimal("0")
            result.credit_card_outstanding += outstanding

        elif t == AccountType.LOAN:
            outstanding = acc.outstanding_balance or Decimal("0")
            result.loan_outstanding += outstanding

        elif t == AccountType.INVESTMENT:
            pass  # handled via portfolio_value

    result.investment_value = portfolio_value
    result.total_assets = result.cash_and_bank + result.investment_value + result.other_assets
    result.total_liabilities = result.loan_outstanding + result.credit_card_outstanding
    result.net_worth = result.total_assets - result.total_liabilities

    return result


def calculate_emergency_fund_coverage(
    essential_monthly_expenses: Decimal,
    liquid_savings: Decimal,
) -> Optional[Decimal]:
    """
    Emergency fund months = liquid savings / essential monthly expenses.
    Returns None if essential expenses are zero (undefined).
    """
    if essential_monthly_expenses <= 0:
        return None
    return (liquid_savings / essential_monthly_expenses).quantize(Decimal("0.1"))
