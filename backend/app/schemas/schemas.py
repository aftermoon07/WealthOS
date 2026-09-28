"""Pydantic schemas for API request/response."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ─── Account ──────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    account_type: str
    institution: str | None = None
    currency: str = "INR"
    outstanding_balance: Decimal | None = None
    loan_principal: Decimal | None = None
    interest_rate: Decimal | None = None
    emi: Decimal | None = None


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
    merchant: str | None = None
    category_id: int | None = None
    transaction_type: str
    transfer_account_id: int | None = None
    reference: str | None = None


class TransactionOut(BaseModel):
    id: int
    date: date
    account_id: int
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    category_id: int | None
    category_name: str | None = None
    transaction_type: str
    duplicate_status: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    category_id: int | None = None
    description: str | None = None
    merchant: str | None = None
    transaction_type: str | None = None


# ─── Investment Transaction ───────────────────────────────────────────────────

class InvestmentTransactionCreate(BaseModel):
    account_id: int
    security_id: int
    date: date
    txn_type: str
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fees: Decimal = Decimal(0)
    taxes: Decimal = Decimal(0)
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
    sector: str | None = None
    asset_class: str | None = None
    currency: str = "INR"
    isin: str | None = None


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
    current_amount: Decimal = Decimal(0)
    target_date: date | None = None
    monthly_contribution: Decimal | None = None
    expected_return_pct: Decimal | None = None
    notes: str | None = None


class GoalOut(GoalCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── AI Assistant ─────────────────────────────────────────────────────────────

class AssistantQuery(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    year: int | None = None
    month: int | None = None


class AssistantResponse(BaseModel):
    summary: str
    evidence: list[str] = []
    drivers: list[str] = []
    watch_items: list[str] = []
    confidence: str
    confidence_reason: str = ""
    tools_called: list[str] = []
    structured_data: dict[str, Any] = {}
    error: str | None = None


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
