"""SQLAlchemy ORM models — all financial entities."""
from __future__ import annotations
import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Numeric, DateTime, Date, Boolean, Text, ForeignKey,
    Enum as SAEnum, Integer, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────


class AccountType(str, enum.Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"
    OTHER = "OTHER"


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    INVESTMENT_BUY = "INVESTMENT_BUY"
    INVESTMENT_SELL = "INVESTMENT_SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    FEE = "FEE"
    REFUND = "REFUND"
    DEBT_PAYMENT = "DEBT_PAYMENT"
    OTHER = "OTHER"


class InvestmentType(str, enum.Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    BOND = "BOND"
    GOLD = "GOLD"
    CRYPTO = "CRYPTO"
    OTHER = "OTHER"


class InvestmentTxnType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    BONUS = "BONUS"
    SPLIT = "SPLIT"
    MERGER = "MERGER"
    SIP = "SIP"
    FEE = "FEE"


class GoalType(str, enum.Enum):
    EMERGENCY_FUND = "EMERGENCY_FUND"
    CAR = "CAR"
    HOUSE = "HOUSE"
    TRAVEL = "TRAVEL"
    EDUCATION = "EDUCATION"
    RETIREMENT = "RETIREMENT"
    OTHER = "OTHER"


class DuplicateStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    REVIEWED = "REVIEWED"


class MarketDataSource(str, enum.Enum):
    LIVE = "LIVE"
    DEMO = "DEMO"
    USER_PROVIDED = "USER_PROVIDED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ─── Models ───────────────────────────────────────────────────────────────────


class Account(Base):
    """Bank account, credit card, or investment account."""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType))
    institution: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # For credit cards / loans: current outstanding balance
    outstanding_balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    # For loans: original principal, interest rate, EMI
    loan_principal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    emi: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        primaryjoin="Transaction.account_id == Account.id",
        foreign_keys="[Transaction.account_id]",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    investment_transactions: Mapped[list[InvestmentTransaction]] = relationship(
        "InvestmentTransaction", back_populates="account"
    )


class Category(Base):
    """Spending/income category."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    parent_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="category_rel"
    )


class Transaction(Base):
    """Normalized financial transaction."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # Always positive
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    description: Mapped[str] = mapped_column(String(500))
    merchant: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    # For transfers: the linked account on the other side
    transfer_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # User-overridden category flag
    category_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_status: Mapped[Optional[DuplicateStatus]] = mapped_column(
        SAEnum(DuplicateStatus), nullable=True
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account"] = relationship(
        "Account",
        primaryjoin="Transaction.account_id == Account.id",
        foreign_keys="[Transaction.account_id]",
        back_populates="transactions",
    )
    category_rel: Mapped[Optional[Category]] = relationship(
        "Category", back_populates="transactions"
    )


class Security(Base):
    """A tradeable security: stock, ETF, mutual fund, etc."""
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    investment_type: Mapped[InvestmentType] = mapped_column(SAEnum(InvestmentType))
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    asset_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    isin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    investment_transactions: Mapped[list[InvestmentTransaction]] = relationship(
        "InvestmentTransaction", back_populates="security"
    )
    market_prices: Mapped[list[MarketPrice]] = relationship(
        "MarketPrice", back_populates="security"
    )


class InvestmentTransaction(Base):
    """Buy, sell, dividend, SIP, etc."""
    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    date: Mapped[date] = mapped_column(Date)
    txn_type: Mapped[InvestmentTxnType] = mapped_column(SAEnum(InvestmentTxnType))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))  # per unit
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    taxes: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped[Account] = relationship(
        "Account", back_populates="investment_transactions"
    )
    security: Mapped[Security] = relationship(
        "Security", back_populates="investment_transactions"
    )


class MarketPrice(Base):
    """Latest (or historical) price for a security."""
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    price_date: Mapped[date] = mapped_column(Date)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source: Mapped[MarketDataSource] = mapped_column(
        SAEnum(MarketDataSource), default=MarketDataSource.DEMO
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    security: Mapped[Security] = relationship(
        "Security", back_populates="market_prices"
    )


class Goal(Base):
    """Financial goal — emergency fund, car, house, etc."""
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    goal_type: Mapped[GoalType] = mapped_column(SAEnum(GoalType))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    monthly_contribution: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    expected_return_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NetWorthSnapshot(Base):
    """Point-in-time net worth record."""
    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
