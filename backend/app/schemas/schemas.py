"""Pydantic schemas for API request/response."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


# ─── Account ──────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    account_type: str
    institution: Optional[str] = None
    currency: str = "INR"
    outstanding_balance: Optional[Decimal] = None
    loan_principal: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    emi: Optional[Decimal] = None


class AccountOut(AccountCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Transaction ──────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    date: date
    account_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = "INR"
    description: str
    merchant: Optional[str] = None
    category_id: Optional[int] = None
    transaction_type: str
    transfer_account_id: Optional[int] = None
    reference: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    date: date
    account_id: int
    amount: Decimal
    currency: str
    description: str
    merchant: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str] = None
    transaction_type: str
    duplicate_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    category_id: Optional[int] = None
    description: Optional[str] = None
    merchant: Optional[str] = None
    transaction_type: Optional[str] = None


# ─── Investment Transaction ───────────────────────────────────────────────────

class InvestmentTransactionCreate(BaseModel):
    account_id: int
    security_id: int
    date: date
    txn_type: str
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fees: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")
    currency: str = "INR"


class InvestmentTransactionOut(InvestmentTransactionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Security ─────────────────────────────────────────────────────────────────

class SecurityCreate(BaseModel):
    ticker: str
    name: str
    investment_type: str
    sector: Optional[str] = None
    asset_class: Optional[str] = None
    currency: str = "INR"
    isin: Optional[str] = None


class SecurityOut(SecurityCreate):
    id: int

    class Config:
        from_attributes = True


# ─── Market Price ─────────────────────────────────────────────────────────────

class MarketPriceCreate(BaseModel):
    security_id: int
    price_date: date
    price: Decimal = Field(..., gt=0)
    source: str = "USER_PROVIDED"


# ─── Goal ─────────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    name: str
    goal_type: str
    target_amount: Decimal = Field(..., gt=0)
    current_amount: Decimal = Decimal("0")
    target_date: Optional[date] = None
    monthly_contribution: Optional[Decimal] = None
    expected_return_pct: Optional[Decimal] = None
    notes: Optional[str] = None


class GoalOut(GoalCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── AI Assistant ─────────────────────────────────────────────────────────────

class AssistantQuery(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = None
    month: Optional[int] = None


class AssistantResponse(BaseModel):
    summary: str
    evidence: list[str] = []
    drivers: list[str] = []
    watch_items: list[str] = []
    confidence: str
    confidence_reason: str = ""
    tools_called: list[str] = []
    structured_data: dict[str, Any] = {}
    error: Optional[str] = None


# ─── CSV Import ───────────────────────────────────────────────────────────────

class CSVImportResult(BaseModel):
    imported_count: int
    invalid_count: int
    duplicate_candidates: int
    warnings: list[str] = []
    errors: list[str] = []
    invalid_rows: list[dict] = []


# ─── Pagination ───────────────────────────────────────────────────────────────

class Paginated(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
