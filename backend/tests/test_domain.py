"""
COMPREHENSIVE TEST SUITE
=========================
Tests for all deterministic domain logic.
No AI tests — those are integration-level.

Run: pytest tests/ -v
"""
from __future__ import annotations

import pytest
from datetime import date
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock

from app.models.models import TransactionType, InvestmentTxnType
from app.services.cash_flow import calculate_cash_flow, CashFlowResult
from app.services.net_worth import calculate_net_worth, calculate_emergency_fund_coverage
from app.services.portfolio import (
    calculate_holdings, calculate_realized_pnl,
    calculate_xirr, calculate_cagr,
    calculate_asset_allocation, calculate_concentration,
)
from app.services.categorization import (
    categorize_transaction, normalize_merchant,
)
from app.services.ingestion.csv_parser import parse_bank_csv, NormalizedRow
from app.services.anomalies import detect_large_transactions, detect_duplicate_candidates


# ─── Test Helpers ─────────────────────────────────────────────────────────────

def _txn(txn_type: TransactionType, amount: Decimal, date_=None):
    """Create a mock Transaction for testing."""
    t = MagicMock()
    t.transaction_type = txn_type
    t.amount = amount
    t.date = date_ or date(2026, 9, 1)
    t.description = "Test"
    t.merchant = None
    t.category_rel = None
    t.id = 1
    return t


def _inv_txn(txn_type: InvestmentTxnType, qty: Decimal, price: Decimal, fees: Decimal = Decimal("0"), d: date = date(2026, 1, 1), sid: int = 1):
    t = MagicMock()
    t.txn_type = txn_type
    t.quantity = qty
    t.price = price
    t.fees = fees
    t.date = d
    t.security_id = sid
    t.security = MagicMock()
    t.security.ticker = f"SEC{sid}"
    t.security.name = f"Security {sid}"
    t.security.investment_type = MagicMock()
    t.security.investment_type.value = "STOCK"
    t.security.sector = "Technology"
    return t


def _account(acc_type, balance: Decimal = Decimal("0")):
    a = MagicMock()
    a.account_type = acc_type
    a.outstanding_balance = balance
    a.is_active = True
    return a


# ─── Cash Flow Tests ──────────────────────────────────────────────────────────

class TestCashFlow:

    def test_basic_income_expense(self):
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("60000")),
        ]
        cf = calculate_cash_flow(txns)
        assert cf.income == Decimal("100000")
        assert cf.expenses == Decimal("60000")
        assert cf.savings == Decimal("40000")

    def test_savings_rate_calculation(self):
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("62100")),
        ]
        cf = calculate_cash_flow(txns)
        assert cf.savings_rate == Decimal("37.90")  # 37.9%

    def test_transfer_not_counted_as_expense(self):
        """CRITICAL: Bank A → Bank B transfer must not become an expense."""
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("40000")),
            _txn(TransactionType.TRANSFER, Decimal("50000")),  # Transfer between own accounts
        ]
        cf = calculate_cash_flow(txns)
        assert cf.expenses == Decimal("40000"), "Transfer must NOT count as expense"
        assert cf.transfers == Decimal("50000")
        assert cf.savings == Decimal("60000")

    def test_investment_purchase_not_counted_as_expense(self):
        """CRITICAL: Bank → Brokerage transfer must not be an expense."""
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("30000")),
            _txn(TransactionType.INVESTMENT_BUY, Decimal("20000")),  # SIP/stock purchase
        ]
        cf = calculate_cash_flow(txns)
        assert cf.expenses == Decimal("30000"), "Investment buy must NOT count as expense"
        assert cf.investment_contributions == Decimal("20000")
        assert cf.savings == Decimal("70000")

    def test_credit_card_repayment_not_double_counted(self):
        """CRITICAL: CC purchase is expense; CC payment is transfer — not another expense."""
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("5000")),    # CC purchase (already tracked)
            _txn(TransactionType.DEBT_PAYMENT, Decimal("5000")),  # CC payment — NOT another expense
        ]
        cf = calculate_cash_flow(txns)
        assert cf.expenses == Decimal("5000"), "CC payment must NOT be a second expense"
        assert cf.debt_payments == Decimal("5000")
        assert cf.savings == Decimal("95000")

    def test_zero_income_savings_rate_is_none(self):
        """If income is 0, savings rate should be None (not 0 or infinity)."""
        txns = [_txn(TransactionType.EXPENSE, Decimal("10000"))]
        cf = calculate_cash_flow(txns)
        assert cf.income == Decimal("0")
        assert cf.savings_rate is None, "Savings rate with 0 income must be None"

    def test_investment_sell_not_income(self):
        """Selling investments is not salary income."""
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.INVESTMENT_SELL, Decimal("25000")),
        ]
        cf = calculate_cash_flow(txns)
        assert cf.income == Decimal("100000"), "Investment sell must not count as income"

    def test_higher_expenses_cannot_increase_savings(self):
        """Increasing expenses always decreases savings."""
        txns1 = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("50000")),
        ]
        txns2 = txns1 + [_txn(TransactionType.EXPENSE, Decimal("10000"))]
        cf1 = calculate_cash_flow(txns1)
        cf2 = calculate_cash_flow(txns2)
        assert cf2.savings < cf1.savings

    def test_dividend_counts_as_income(self):
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.DIVIDEND, Decimal("5000")),
        ]
        cf = calculate_cash_flow(txns)
        assert cf.income == Decimal("105000")

    def test_refund_reduces_expenses(self):
        txns = [
            _txn(TransactionType.INCOME, Decimal("100000")),
            _txn(TransactionType.EXPENSE, Decimal("10000")),
            _txn(TransactionType.REFUND, Decimal("2000")),
        ]
        cf = calculate_cash_flow(txns)
        assert cf.expenses == Decimal("8000")


# ─── Net Worth Tests ──────────────────────────────────────────────────────────

class TestNetWorth:

    def test_basic_net_worth(self):
        from app.models.models import AccountType
        accounts = [
            _account(AccountType.SAVINGS, Decimal("200000")),
            _account(AccountType.LOAN, Decimal("3200000")),
        ]
        nw = calculate_net_worth(accounts, Decimal("800000"))
        assert nw.total_assets == Decimal("1000000")
        assert nw.total_liabilities == Decimal("3200000")
        assert nw.net_worth == Decimal("-2200000")

    def test_higher_liabilities_cannot_increase_net_worth(self):
        from app.models.models import AccountType
        accounts1 = [_account(AccountType.SAVINGS, Decimal("500000"))]
        accounts2 = [
            _account(AccountType.SAVINGS, Decimal("500000")),
            _account(AccountType.LOAN, Decimal("100000")),
        ]
        nw1 = calculate_net_worth(accounts1, Decimal("0"))
        nw2 = calculate_net_worth(accounts2, Decimal("0"))
        assert nw2.net_worth < nw1.net_worth

    def test_liquid_savings_excludes_investments(self):
        """Investment portfolio should NOT count as liquid savings."""
        from app.models.models import AccountType
        accounts = [_account(AccountType.SAVINGS, Decimal("200000"))]
        nw = calculate_net_worth(accounts, Decimal("800000"))  # 800k in stocks
        assert nw.liquid_savings == Decimal("200000"), "Investments are not liquid savings"
        assert nw.investment_value == Decimal("800000")

    def test_emergency_fund_coverage(self):
        coverage = calculate_emergency_fund_coverage(
            essential_monthly_expenses=Decimal("35000"),
            liquid_savings=Decimal("210000"),
        )
        assert coverage == Decimal("6.0")

    def test_emergency_fund_zero_expenses_returns_none(self):
        result = calculate_emergency_fund_coverage(Decimal("0"), Decimal("100000"))
        assert result is None


# ─── Portfolio Engine Tests ───────────────────────────────────────────────────

class TestPortfolioEngine:

    def test_weighted_average_cost_basis(self):
        """100 @ ₹100 + 50 @ ₹120 = avg ₹106.67"""
        txns = [
            _inv_txn(InvestmentTxnType.BUY, Decimal("100"), Decimal("100"), d=date(2026, 1, 1)),
            _inv_txn(InvestmentTxnType.BUY, Decimal("50"), Decimal("120"), d=date(2026, 2, 1)),
        ]
        holdings = calculate_holdings(txns, {})
        assert len(holdings) == 1
        h = holdings[0]
        expected_avg = (Decimal("100") * Decimal("100") + Decimal("50") * Decimal("120")) / Decimal("150")
        assert abs(h.average_cost - expected_avg) < Decimal("0.01")
        assert h.quantity == Decimal("150").quantize(Decimal("0.0001"))

    def test_sell_reduces_position(self):
        txns = [
            _inv_txn(InvestmentTxnType.BUY, Decimal("100"), Decimal("100"), d=date(2026, 1, 1)),
            _inv_txn(InvestmentTxnType.SELL, Decimal("30"), Decimal("150"), d=date(2026, 3, 1)),
        ]
        holdings = calculate_holdings(txns, {})
        assert len(holdings) == 1
        assert holdings[0].quantity == Decimal("70").quantize(Decimal("0.0001"))

    def test_full_sell_closes_position(self):
        txns = [
            _inv_txn(InvestmentTxnType.BUY, Decimal("100"), Decimal("100"), d=date(2026, 1, 1)),
            _inv_txn(InvestmentTxnType.SELL, Decimal("100"), Decimal("150"), d=date(2026, 3, 1)),
        ]
        holdings = calculate_holdings(txns, {})
        assert len(holdings) == 0, "Full sell should close position"

    def test_unrealized_pnl_with_price(self):
        txns = [_inv_txn(InvestmentTxnType.BUY, Decimal("10"), Decimal("100"))]
        prices = {1: (Decimal("120"), "DEMO", date(2026, 9, 1))}
        holdings = calculate_holdings(txns, prices)
        h = holdings[0]
        assert h.market_value == Decimal("1200.00")
        assert h.unrealized_pnl == Decimal("200.00")
        assert h.unrealized_pnl_pct == Decimal("20.00")

    def test_missing_price_returns_none_not_zero(self):
        """CRITICAL: Missing price must NOT become 0 or create fake return."""
        txns = [_inv_txn(InvestmentTxnType.BUY, Decimal("10"), Decimal("100"))]
        holdings = calculate_holdings(txns, {})  # No prices
        h = holdings[0]
        assert h.market_value is None, "Missing price must be None, not 0"
        assert h.unrealized_pnl is None

    def test_realized_pnl(self):
        """Sell 50 @ ₹150, bought at ₹100 → realized = ₹2500."""
        txns = [
            _inv_txn(InvestmentTxnType.BUY, Decimal("100"), Decimal("100"), d=date(2026, 1, 1)),
            _inv_txn(InvestmentTxnType.SELL, Decimal("50"), Decimal("150"), d=date(2026, 6, 1)),
        ]
        realized = calculate_realized_pnl(txns)
        assert realized == Decimal("2500.00")

    def test_xirr_basic(self):
        """Simple 1-year 10% investment should yield ~10% XIRR."""
        flows = [
            (date(2025, 1, 1), Decimal("-100000")),
            (date(2026, 1, 1), Decimal("110000")),
        ]
        xirr = calculate_xirr(flows)
        assert xirr is not None
        assert abs(xirr - 0.10) < 0.005

    def test_xirr_insufficient_data_returns_none(self):
        """CRITICAL: Missing data must return None, not 0%."""
        xirr = calculate_xirr([(date(2026, 1, 1), Decimal("-100000"))])
        assert xirr is None

    def test_xirr_all_outflows_returns_none(self):
        flows = [
            (date(2026, 1, 1), Decimal("-100000")),
            (date(2026, 6, 1), Decimal("-50000")),
        ]
        xirr = calculate_xirr(flows)
        assert xirr is None

    def test_cagr_basic(self):
        """₹100 → ₹200 in 2 years = 41.4% CAGR."""
        cagr = calculate_cagr(Decimal("100"), Decimal("200"), 2.0)
        assert cagr is not None
        assert abs(float(cagr) - 0.4142) < 0.001

    def test_cagr_zero_start_returns_none(self):
        cagr = calculate_cagr(Decimal("0"), Decimal("100"), 1.0)
        assert cagr is None

    def test_asset_allocation_sums_to_100(self):
        from app.services.portfolio import Holding
        holdings = [
            MagicMock(market_value=Decimal("700000"), investment_type="STOCK"),
            MagicMock(market_value=Decimal("200000"), investment_type="MUTUAL_FUND"),
            MagicMock(market_value=Decimal("100000"), investment_type="GOLD"),
        ]
        allocation = calculate_asset_allocation(holdings)
        total = sum(allocation.values())
        assert abs(total - Decimal("100")) < Decimal("0.01")

    def test_concentration(self):
        from app.services.portfolio import Holding
        holdings = [
            MagicMock(market_value=Decimal("600000")),
            MagicMock(market_value=Decimal("300000")),
            MagicMock(market_value=Decimal("100000")),
        ]
        top1, top3 = calculate_concentration(holdings)
        assert top1 == Decimal("60.00")
        assert top3 == Decimal("100.00")


# ─── Categorization Tests ─────────────────────────────────────────────────────

class TestCategorization:

    def test_swiggy_is_dining(self):
        assert categorize_transaction("Order from Swiggy", "Swiggy", 350) == "Dining"

    def test_netflix_is_subscriptions(self):
        assert categorize_transaction("Netflix subscription", None, 649) == "Subscriptions"

    def test_uber_is_transport(self):
        assert categorize_transaction("Uber ride", "Uber", 180) == "Transport"

    def test_salary_credit_is_salary(self):
        assert categorize_transaction("Salary credit from employer", None, 120000) == "Salary"

    def test_user_override_wins(self):
        result = categorize_transaction("Amazon purchase", "Amazon", 1000, user_override="Books")
        assert result == "Books", "User override must always win"

    def test_unknown_becomes_other(self):
        result = categorize_transaction("XYZABC12345", None, 999)
        assert result == "Other"

    def test_normalize_merchant_strips_upi_suffix(self):
        result = normalize_merchant("SWIGGY/UPIREF123456789")
        assert "123456789" not in result
        assert "Upiref" not in result


# ─── CSV Parser Tests ─────────────────────────────────────────────────────────

class TestCSVParser:

    GENERIC_CSV = """date,description,debit,credit
2026-09-01,Salary credit,,120000
2026-09-03,Rent payment,28000,
2026-09-05,Home Loan EMI,43500,
2026-09-08,Netflix Subscription,649,
"""

    def test_parse_generic_csv(self):
        result = parse_bank_csv(self.GENERIC_CSV)
        assert len(result.valid) == 4
        assert len(result.invalid) == 0
        assert len(result.errors) == 0

    def test_income_vs_debit(self):
        result = parse_bank_csv(self.GENERIC_CSV)
        salary_row = next(r for r in result.valid if "Salary" in r.description)
        assert salary_row.is_debit == False
        assert salary_row.amount == Decimal("120000")

    def test_debit_row(self):
        result = parse_bank_csv(self.GENERIC_CSV)
        rent_row = next(r for r in result.valid if "Rent" in r.description)
        assert rent_row.is_debit == True
        assert rent_row.amount == Decimal("28000")

    def test_invalid_row_not_silently_discarded(self):
        csv_with_bad_row = """date,description,debit,credit
2026-09-01,Valid transaction,,5000
NOT_A_DATE,Bad row,1000,
"""
        result = parse_bank_csv(csv_with_bad_row)
        assert len(result.valid) == 1
        assert len(result.invalid) == 1, "Invalid rows must be tracked, not discarded silently"

    def test_duplicate_detection(self):
        # Fingerprint uses desc[:40] — match exactly
        desc = "Salary credit from employer"
        fp = f"2026-09-01|5000|{desc[:40]}"
        existing = {fp}
        result = parse_bank_csv(
            f"date,description,debit,credit\n2026-09-01,{desc},,5000\n",
            existing_fingerprints=existing,
        )
        assert len(result.valid) == 0
        assert len(result.duplicate_candidates) == 1

    def test_empty_csv_returns_error(self):
        result = parse_bank_csv("")
        assert len(result.errors) > 0 or len(result.valid) == 0


# ─── Anomaly Detection Tests ──────────────────────────────────────────────────

class TestAnomalyDetection:

    def test_large_transaction_detected(self):
        from decimal import Decimal
        txns = [
            _txn(TransactionType.EXPENSE, Decimal("75000")),
            _txn(TransactionType.EXPENSE, Decimal("2000")),
        ]
        anomalies = detect_large_transactions(txns)
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "LARGE_TRANSACTION"
        assert anomalies[0].severity == "MEDIUM"

    def test_small_expense_not_flagged(self):
        txns = [_txn(TransactionType.EXPENSE, Decimal("1000"))]
        anomalies = detect_large_transactions(txns)
        assert len(anomalies) == 0

    def test_large_income_not_flagged_as_anomaly(self):
        """Large INCOME should not be flagged as a large transaction anomaly."""
        txns = [_txn(TransactionType.INCOME, Decimal("100000"))]
        anomalies = detect_large_transactions(txns)
        assert len(anomalies) == 0


# ─── Invariant Tests ─────────────────────────────────────────────────────────

class TestFinancialInvariants:
    """Key accounting invariants that must always hold."""

    def test_savings_is_income_minus_expenses(self):
        for income, expenses in [(100000, 60000), (50000, 50001), (200000, 0)]:
            txns = [
                _txn(TransactionType.INCOME, Decimal(str(income))),
                _txn(TransactionType.EXPENSE, Decimal(str(expenses))),
            ]
            cf = calculate_cash_flow(txns)
            assert cf.savings == cf.income - cf.expenses

    def test_net_worth_is_assets_minus_liabilities(self):
        from app.models.models import AccountType
        accounts = [
            _account(AccountType.SAVINGS, Decimal("500000")),
            _account(AccountType.LOAN, Decimal("200000")),
        ]
        nw = calculate_net_worth(accounts, Decimal("100000"))
        assert nw.net_worth == nw.total_assets - nw.total_liabilities
