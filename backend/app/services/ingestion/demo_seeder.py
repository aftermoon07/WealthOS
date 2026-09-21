"""
REALISTIC 12-MONTH DEMO DATA SEEDER
=====================================
Fictional demo data — NOT real financial data.
Covers: salary, rent, food, SIPs, stocks, EMIs, travel, subscriptions.

Designed to exercise:
- Cash flow engine (correct transfer handling)
- Portfolio engine (XIRR, holdings, allocation)
- Anomaly detection (spending spike in August travel)
- Categorization
- Goals
- AI analysis
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import (
    Account, AccountType, Category, TransactionType, Transaction,
    Security, InvestmentType, InvestmentTransaction, InvestmentTxnType,
    MarketPrice, MarketDataSource, Goal, GoalType, NetWorthSnapshot,
)
from app.db.database import SessionLocal, init_db


# ─── Helper ────────────────────────────────────────────────────────────────────

def _d(v: str) -> Decimal:
    return Decimal(v)


async def clear_all(db: AsyncSession) -> None:
    """Clear demo data for re-seeding."""
    for model in [
        NetWorthSnapshot, MarketPrice, InvestmentTransaction,
        Transaction, Goal, Security, Category, Account,
    ]:
        result = await db.execute(select(model))
        for obj in result.scalars().all():
            await db.delete(obj)
    await db.commit()


async def seed_demo_data(db: AsyncSession, force: bool = False) -> None:
    """Seed realistic 12-month demo dataset."""

    # Check if already seeded
    existing = await db.execute(select(Account))
    if existing.scalars().first() and not force:
        return

    if force:
        await clear_all(db)

    # ─── Accounts ───────────────────────────────────────────────────────────
    hdfc_savings = Account(
        name="HDFC Savings Account",
        account_type=AccountType.SAVINGS,
        institution="HDFC Bank",
        currency="INR",
        outstanding_balance=_d("210000"),  # Current balance
    )
    hdfc_cc = Account(
        name="HDFC Regalia Credit Card",
        account_type=AccountType.CREDIT_CARD,
        institution="HDFC Bank",
        outstanding_balance=_d("18500"),  # Current outstanding
    )
    icici_savings = Account(
        name="ICICI Savings Account",
        account_type=AccountType.SAVINGS,
        institution="ICICI Bank",
        outstanding_balance=_d("85000"),
    )
    zerodha_demat = Account(
        name="Zerodha Demat Account",
        account_type=AccountType.INVESTMENT,
        institution="Zerodha",
        outstanding_balance=_d("0"),
    )
    home_loan = Account(
        name="HDFC Home Loan",
        account_type=AccountType.LOAN,
        institution="HDFC Bank",
        outstanding_balance=_d("3200000"),
        loan_principal=_d("5000000"),
        interest_rate=_d("8.75"),
        emi=_d("43500"),
    )

    db.add_all([hdfc_savings, hdfc_cc, icici_savings, zerodha_demat, home_loan])
    await db.flush()

    # ─── Categories ─────────────────────────────────────────────────────────
    cats = {
        "Salary": Category(name="Salary", transaction_type=TransactionType.INCOME, is_essential=True),
        "Rent": Category(name="Rent", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Groceries": Category(name="Groceries", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Dining": Category(name="Dining", transaction_type=TransactionType.EXPENSE, is_essential=False),
        "Transport": Category(name="Transport", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Utilities": Category(name="Utilities", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Subscriptions": Category(name="Subscriptions", transaction_type=TransactionType.EXPENSE, is_essential=False),
        "Shopping": Category(name="Shopping", transaction_type=TransactionType.EXPENSE, is_essential=False),
        "Travel": Category(name="Travel", transaction_type=TransactionType.EXPENSE, is_essential=False),
        "Insurance": Category(name="Insurance", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Healthcare": Category(name="Healthcare", transaction_type=TransactionType.EXPENSE, is_essential=True),
        "Loan EMI": Category(name="Loan EMI", transaction_type=TransactionType.DEBT_PAYMENT, is_essential=True),
        "Investment": Category(name="Investment", transaction_type=TransactionType.INVESTMENT_BUY, is_essential=False),
        "Transfer": Category(name="Transfer", transaction_type=TransactionType.TRANSFER, is_essential=False),
        "Dividend": Category(name="Dividend", transaction_type=TransactionType.DIVIDEND, is_essential=False),
        "Education": Category(name="Education", transaction_type=TransactionType.EXPENSE, is_essential=False),
        "Fuel": Category(name="Fuel", transaction_type=TransactionType.EXPENSE, is_essential=True),
    }
    for cat in cats.values():
        db.add(cat)
    await db.flush()

    # ─── Securities ─────────────────────────────────────────────────────────
    reliance = Security(ticker="RELIANCE", name="Reliance Industries Ltd", investment_type=InvestmentType.STOCK, sector="Energy", asset_class="Large Cap")
    infy = Security(ticker="INFY", name="Infosys Ltd", investment_type=InvestmentType.STOCK, sector="IT", asset_class="Large Cap")
    hdfc_bank_s = Security(ticker="HDFCBANK", name="HDFC Bank Ltd", investment_type=InvestmentType.STOCK, sector="Banking", asset_class="Large Cap")
    nifty50_etf = Security(ticker="NIFTY50ETF", name="Nifty 50 ETF", investment_type=InvestmentType.ETF, sector="Diversified", asset_class="Large Cap")
    ppfas = Security(ticker="PPFAS", name="Parag Parikh Flexi Cap Fund", investment_type=InvestmentType.MUTUAL_FUND, sector="Diversified", asset_class="Flexi Cap")
    nippon_gold = Security(ticker="GOLDBEES", name="Nippon India Gold ETF", investment_type=InvestmentType.GOLD, sector="Gold", asset_class="Gold")

    db.add_all([reliance, infy, hdfc_bank_s, nifty50_etf, ppfas, nippon_gold])
    await db.flush()

    # ─── Transactions (12 months: Oct 2025 – Sep 2026) ─────────────────────
    txns = []

    base_year = 2025
    # Monthly recurring pattern
    for month_offset in range(12):
        m = (10 + month_offset - 1) % 12 + 1
        y = base_year + (10 + month_offset - 1) // 12

        # Salary (1st of each month)
        salary_amt = _d("120000") if month_offset < 6 else _d("135000")  # Raise in April
        txns.append(Transaction(
            date=date(y, m, 1),
            account_id=hdfc_savings.id,
            amount=salary_amt,
            description="Salary Credit - TechCorp India Pvt Ltd",
            merchant="TechCorp India",
            category_id=cats["Salary"].id,
            transaction_type=TransactionType.INCOME,
        ))

        # Rent (3rd of each month) — transfer to landlord
        txns.append(Transaction(
            date=date(y, m, 3),
            account_id=hdfc_savings.id,
            amount=_d("28000"),
            description="Rent Payment - Apartment 4B",
            merchant="Landlord",
            category_id=cats["Rent"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Home loan EMI — this is DEBT_PAYMENT, not expense
        txns.append(Transaction(
            date=date(y, m, 5),
            account_id=hdfc_savings.id,
            amount=_d("43500"),
            description="Home Loan EMI - HDFC",
            merchant="HDFC Bank",
            category_id=cats["Loan EMI"].id,
            transaction_type=TransactionType.DEBT_PAYMENT,
        ))

        # Groceries
        txns.append(Transaction(
            date=date(y, m, 8),
            account_id=hdfc_cc.id,
            amount=_d("6800"),
            description="BigBasket Monthly Groceries",
            merchant="BigBasket",
            category_id=cats["Groceries"].id,
            transaction_type=TransactionType.EXPENSE,
        ))
        txns.append(Transaction(
            date=date(y, m, 22),
            account_id=hdfc_cc.id,
            amount=_d("3200"),
            description="DMart Groceries",
            merchant="DMart",
            category_id=cats["Groceries"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Dining (variable)
        dining_base = _d("5500")
        dining = dining_base + _d("2300") if month_offset == 10 else dining_base  # September spike
        txns.append(Transaction(
            date=date(y, m, 14),
            account_id=hdfc_cc.id,
            amount=dining,
            description="Monthly dining expenses",
            merchant="Various Restaurants",
            category_id=cats["Dining"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Utilities
        txns.append(Transaction(
            date=date(y, m, 10),
            account_id=hdfc_savings.id,
            amount=_d("2800"),
            description="Electricity Bill - BESCOM",
            merchant="BESCOM",
            category_id=cats["Utilities"].id,
            transaction_type=TransactionType.EXPENSE,
        ))
        txns.append(Transaction(
            date=date(y, m, 10),
            account_id=hdfc_savings.id,
            amount=_d("899"),
            description="Jio Postpaid - Mobile",
            merchant="Jio",
            category_id=cats["Utilities"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Subscriptions
        txns.append(Transaction(
            date=date(y, m, 15),
            account_id=hdfc_cc.id,
            amount=_d("649"),
            description="Netflix Subscription",
            merchant="Netflix",
            category_id=cats["Subscriptions"].id,
            transaction_type=TransactionType.EXPENSE,
        ))
        txns.append(Transaction(
            date=date(y, m, 15),
            account_id=hdfc_cc.id,
            amount=_d("119"),
            description="Spotify Premium",
            merchant="Spotify",
            category_id=cats["Subscriptions"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Transport
        txns.append(Transaction(
            date=date(y, m, 18),
            account_id=hdfc_cc.id,
            amount=_d("2400"),
            description="Uber rides",
            merchant="Uber",
            category_id=cats["Transport"].id,
            transaction_type=TransactionType.EXPENSE,
        ))
        txns.append(Transaction(
            date=date(y, m, 20),
            account_id=hdfc_savings.id,
            amount=_d("3200"),
            description="Petrol - Indian Oil",
            merchant="Indian Oil",
            category_id=cats["Fuel"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Insurance (annual → monthly for simplicity)
        txns.append(Transaction(
            date=date(y, m, 2),
            account_id=hdfc_savings.id,
            amount=_d("4200"),
            description="HDFC Life Term Insurance Premium",
            merchant="HDFC Life",
            category_id=cats["Insurance"].id,
            transaction_type=TransactionType.EXPENSE,
        ))

        # Credit card payment — this is TRANSFER, NOT expense
        # (The credit card expenses are already tracked above)
        txns.append(Transaction(
            date=date(y, m, 25),
            account_id=hdfc_savings.id,
            amount=_d("22000"),
            description="HDFC Credit Card Payment",
            merchant="HDFC Bank",
            category_id=cats["Transfer"].id,
            transaction_type=TransactionType.TRANSFER,  # ← CRITICAL: not expense
            transfer_account_id=hdfc_cc.id,
        ))

        # Transfer to ICICI for savings
        txns.append(Transaction(
            date=date(y, m, 28),
            account_id=hdfc_savings.id,
            amount=_d("20000"),
            description="Transfer to ICICI Savings",
            merchant="ICICI Bank",
            category_id=cats["Transfer"].id,
            transaction_type=TransactionType.TRANSFER,  # ← CRITICAL: not expense
            transfer_account_id=icici_savings.id,
        ))

    # ─── Travel (August — anomaly trigger) ───────────────────────────────────
    txns.append(Transaction(
        date=date(2026, 8, 10),
        account_id=hdfc_cc.id,
        amount=_d("32000"),
        description="MakeMyTrip - Goa Flight + Hotel",
        merchant="MakeMyTrip",
        category_id=cats["Travel"].id,
        transaction_type=TransactionType.EXPENSE,
    ))
    txns.append(Transaction(
        date=date(2026, 8, 14),
        account_id=hdfc_cc.id,
        amount=_d("18500"),
        description="Hotels.com - Goa Resort",
        merchant="Hotels.com",
        category_id=cats["Travel"].id,
        transaction_type=TransactionType.EXPENSE,
    ))

    # ─── Shopping spikes ─────────────────────────────────────────────────────
    txns.append(Transaction(
        date=date(2026, 7, 20),
        account_id=hdfc_cc.id,
        amount=_d("12800"),
        description="Amazon - Electronics Purchase",
        merchant="Amazon",
        category_id=cats["Shopping"].id,
        transaction_type=TransactionType.EXPENSE,
    ))
    txns.append(Transaction(
        date=date(2026, 11, 12),
        account_id=hdfc_cc.id,
        amount=_d("8900"),
        description="Myntra - Big Fashion Sale",
        merchant="Myntra",
        category_id=cats["Shopping"].id,
        transaction_type=TransactionType.EXPENSE,
    ) if False else None)  # Skip this one — it's after our demo period

    for t in txns:
        if t is not None:
            db.add(t)
    await db.flush()

    # ─── Investment Transactions (SIPs + Stock Purchases) ────────────────────
    inv_txns = []

    # PPFAS SIP — monthly ₹10,000 for 12 months
    ppfas_prices = [420, 435, 428, 442, 455, 448, 461, 470, 458, 475, 489, 495]
    for i, price in enumerate(ppfas_prices):
        m = (10 + i - 1) % 12 + 1
        y = base_year + (10 + i - 1) // 12
        units = 10000 / price
        inv_txns.append(InvestmentTransaction(
            account_id=zerodha_demat.id,
            security_id=ppfas.id,
            date=date(y, m, 7),
            txn_type=InvestmentTxnType.SIP,
            quantity=Decimal(str(round(units, 4))),
            price=Decimal(str(price)),
            fees=_d("0"),
        ))

    # Nifty 50 ETF SIP — monthly ₹5,000
    nifty_prices = [215, 219, 217, 224, 228, 225, 232, 236, 231, 238, 242, 245]
    for i, price in enumerate(nifty_prices):
        m = (10 + i - 1) % 12 + 1
        y = base_year + (10 + i - 1) // 12
        units = 5000 / price
        inv_txns.append(InvestmentTransaction(
            account_id=zerodha_demat.id,
            security_id=nifty50_etf.id,
            date=date(y, m, 7),
            txn_type=InvestmentTxnType.SIP,
            quantity=Decimal(str(round(units, 4))),
            price=Decimal(str(price)),
            fees=_d("0"),
        ))

    # Direct stock purchases
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=reliance.id,
        date=date(2025, 10, 15),
        txn_type=InvestmentTxnType.BUY,
        quantity=_d("20"),
        price=_d("2450"),
        fees=_d("25"),
    ))
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=reliance.id,
        date=date(2026, 2, 10),
        txn_type=InvestmentTxnType.BUY,
        quantity=_d("10"),
        price=_d("2680"),
        fees=_d("15"),
    ))
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=infy.id,
        date=date(2025, 11, 8),
        txn_type=InvestmentTxnType.BUY,
        quantity=_d("15"),
        price=_d("1580"),
        fees=_d("20"),
    ))
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=hdfc_bank_s.id,
        date=date(2026, 1, 12),
        txn_type=InvestmentTxnType.BUY,
        quantity=_d("25"),
        price=_d("1650"),
        fees=_d("30"),
    ))

    # Gold ETF
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=nippon_gold.id,
        date=date(2026, 3, 5),
        txn_type=InvestmentTxnType.BUY,
        quantity=_d("50"),
        price=_d("580"),
        fees=_d("10"),
    ))

    # One sell — partial INFY exit
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=infy.id,
        date=date(2026, 6, 20),
        txn_type=InvestmentTxnType.SELL,
        quantity=_d("5"),
        price=_d("1820"),
        fees=_d("15"),
    ))

    # Dividend from HDFC Bank
    inv_txns.append(InvestmentTransaction(
        account_id=zerodha_demat.id,
        security_id=hdfc_bank_s.id,
        date=date(2026, 7, 15),
        txn_type=InvestmentTxnType.DIVIDEND,
        quantity=_d("25"),  # shares
        price=_d("19"),     # dividend per share
        fees=_d("0"),
    ))

    for t in inv_txns:
        db.add(t)
    await db.flush()

    # ─── Market Prices (DEMO — as of Sep 17, 2026) ───────────────────────────
    demo_prices = [
        MarketPrice(security_id=reliance.id, price_date=date(2026, 9, 17), price=_d("2890"), source=MarketDataSource.DEMO),
        MarketPrice(security_id=infy.id, price_date=date(2026, 9, 17), price=_d("1940"), source=MarketDataSource.DEMO),
        MarketPrice(security_id=hdfc_bank_s.id, price_date=date(2026, 9, 17), price=_d("1780"), source=MarketDataSource.DEMO),
        MarketPrice(security_id=nifty50_etf.id, price_date=date(2026, 9, 17), price=_d("252"), source=MarketDataSource.DEMO),
        MarketPrice(security_id=ppfas.id, price_date=date(2026, 9, 17), price=_d("512"), source=MarketDataSource.DEMO),
        MarketPrice(security_id=nippon_gold.id, price_date=date(2026, 9, 17), price=_d("635"), source=MarketDataSource.DEMO),
    ]
    for p in demo_prices:
        db.add(p)

    # ─── Goals ───────────────────────────────────────────────────────────────
    goals = [
        Goal(
            name="Emergency Fund",
            goal_type=GoalType.EMERGENCY_FUND,
            target_amount=_d("300000"),  # 6 months essential expenses
            current_amount=_d("210000"),
            target_date=date(2027, 3, 31),
            monthly_contribution=_d("7500"),
        ),
        Goal(
            name="International Vacation",
            goal_type=GoalType.TRAVEL,
            target_amount=_d("200000"),
            current_amount=_d("45000"),
            target_date=date(2027, 12, 31),
            monthly_contribution=_d("10000"),
        ),
        Goal(
            name="Early Retirement Corpus",
            goal_type=GoalType.RETIREMENT,
            target_amount=_d("30000000"),
            current_amount=_d("840000"),
            target_date=date(2045, 1, 1),
            monthly_contribution=_d("25000"),
            expected_return_pct=_d("12"),
        ),
    ]
    for g in goals:
        db.add(g)

    # ─── Net Worth Snapshots (monthly) ───────────────────────────────────────
    snapshots = [
        NetWorthSnapshot(snapshot_date=date(2025, 10, 31), total_assets=_d("3920000"), total_liabilities=_d("3250000"), net_worth=_d("670000")),
        NetWorthSnapshot(snapshot_date=date(2025, 11, 30), total_assets=_d("3985000"), total_liabilities=_d("3220000"), net_worth=_d("765000")),
        NetWorthSnapshot(snapshot_date=date(2025, 12, 31), total_assets=_d("4050000"), total_liabilities=_d("3190000"), net_worth=_d("860000")),
        NetWorthSnapshot(snapshot_date=date(2026, 1, 31), total_assets=_d("4130000"), total_liabilities=_d("3162000"), net_worth=_d("968000")),
        NetWorthSnapshot(snapshot_date=date(2026, 2, 28), total_assets=_d("4195000"), total_liabilities=_d("3135000"), net_worth=_d("1060000")),
        NetWorthSnapshot(snapshot_date=date(2026, 3, 31), total_assets=_d("4280000"), total_liabilities=_d("3108000"), net_worth=_d("1172000")),
        NetWorthSnapshot(snapshot_date=date(2026, 4, 30), total_assets=_d("4390000"), total_liabilities=_d("3082000"), net_worth=_d("1308000")),
        NetWorthSnapshot(snapshot_date=date(2026, 5, 31), total_assets=_d("4460000"), total_liabilities=_d("3055000"), net_worth=_d("1405000")),
        NetWorthSnapshot(snapshot_date=date(2026, 6, 30), total_assets=_d("4520000"), total_liabilities=_d("3029000"), net_worth=_d("1491000")),
        NetWorthSnapshot(snapshot_date=date(2026, 7, 31), total_assets=_d("4595000"), total_liabilities=_d("3003000"), net_worth=_d("1592000")),
        NetWorthSnapshot(snapshot_date=date(2026, 8, 31), total_assets=_d("4590000"), total_liabilities=_d("2978000"), net_worth=_d("1612000")),
        NetWorthSnapshot(snapshot_date=date(2026, 9, 17), total_assets=_d("4640000"), total_liabilities=_d("2953000"), net_worth=_d("1687000")),
    ]
    for s in snapshots:
        db.add(s)

    await db.commit()
    print("✅ Demo data seeded successfully.")


if __name__ == "__main__":
    async def main():
        await init_db()
        async with SessionLocal() as db:
            await seed_demo_data(db, force=True)

    asyncio.run(main())
