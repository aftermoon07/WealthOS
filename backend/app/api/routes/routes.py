"""All API routes — single file for simplicity (modular monolith)."""
from __future__ import annotations

import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import (
    Account, Transaction, TransactionType, InvestmentTransaction,
    Security, MarketPrice, Goal, Category, NetWorthSnapshot,
    MarketDataSource,
)
from app.schemas.schemas import (
    AccountCreate, AccountOut, TransactionCreate, TransactionOut,
    TransactionUpdate, InvestmentTransactionCreate, InvestmentTransactionOut,
    SecurityCreate, SecurityOut, MarketPriceCreate, GoalCreate, GoalOut,
    AssistantQuery, AssistantResponse, CSVImportResult,
)
from app.services.cash_flow import calculate_cash_flow
from app.services.net_worth import calculate_net_worth, calculate_emergency_fund_coverage
from app.services.portfolio import assemble_portfolio_metrics
from app.services.spending import analyze_spending
from app.services.anomalies import detect_all_anomalies
from app.services.goals import analyze_goal
from app.services.ai.agent.financial_agent import run_financial_agent
from app.services.ingestion.csv_parser import parse_bank_csv
from app.services.categorization import categorize_transaction, normalize_merchant
from app.core.config import get_settings

router = APIRouter()


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": str(date.today())}

# ─── Demo ─────────────────────────────────────────────────────────────────────

@router.post("/demo/seed")
async def seed_demo(force: bool = False, db: AsyncSession = Depends(get_db)):
    """Seed demo data. Use force=true to re-seed."""
    from app.services.ingestion.demo_seeder import seed_demo_data
    await seed_demo_data(db, force=force)
    return {"status": "seeded"}



# ─── Demo ─────────────────────────────────────────────────────────────────────

@router.post("/demo/seed")
async def seed_demo(force: bool = False, db: AsyncSession = Depends(get_db)):
    """Seed demo data. Use force=true to re-seed."""
    from app.services.ingestion.demo_seeder import seed_demo_data
    await seed_demo_data(db, force=force)
    return {"status": "seeded"}


# ─── Accounts ─────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.is_active == True))
    return result.scalars().all()


@router.post("/accounts", response_model=AccountOut)
async def create_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "Account not found")
    acc.is_active = False
    await db.commit()
    return {"status": "deactivated"}


# ─── Transactions ─────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    account_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction).order_by(Transaction.date.desc())
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if transaction_type:
        q = q.where(Transaction.transaction_type == transaction_type)
    if year and month:
        from_d = date(year, month, 1)
        to_d = date(year, month + 1 if month < 12 else 1, 1) if month < 12 else date(year + 1, 1, 1)
        q = q.where(and_(Transaction.date >= from_d, Transaction.date < to_d))
    elif year:
        q = q.where(and_(Transaction.date >= date(year, 1, 1), Transaction.date < date(year + 1, 1, 1)))

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    txns = result.scalars().all()

    out = []
    for t in txns:
        cat_name = None
        if t.category_id:
            cat_r = await db.execute(select(Category).where(Category.id == t.category_id))
            cat = cat_r.scalar_one_or_none()
            cat_name = cat.name if cat else None
        out.append(TransactionOut(
            id=t.id, date=t.date, account_id=t.account_id, amount=t.amount,
            currency=t.currency, description=t.description, merchant=t.merchant,
            category_id=t.category_id, category_name=cat_name,
            transaction_type=t.transaction_type.value,
            duplicate_status=t.duplicate_status.value if t.duplicate_status else None,
            created_at=t.created_at,
        ))
    return out


@router.post("/transactions", response_model=TransactionOut)
async def create_transaction(payload: TransactionCreate, db: AsyncSession = Depends(get_db)):
    txn = Transaction(**payload.model_dump())
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return TransactionOut(
        id=txn.id, date=txn.date, account_id=txn.account_id, amount=txn.amount,
        currency=txn.currency, description=txn.description, merchant=txn.merchant,
        category_id=txn.category_id, transaction_type=txn.transaction_type.value,
        duplicate_status=None, created_at=txn.created_at,
    )


@router.patch("/transactions/{txn_id}", response_model=dict)
async def update_transaction(txn_id: int, payload: TransactionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    updates = payload.model_dump(exclude_none=True)
    if "category_id" in updates:
        txn.category_id = updates["category_id"]
        txn.category_overridden = True
    for k, v in updates.items():
        if k != "category_id":
            setattr(txn, k, v)
    await db.commit()
    return {"status": "updated"}


# ─── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    cats = result.scalars().all()
    return [{"id": c.id, "name": c.name, "transaction_type": c.transaction_type.value, "is_essential": c.is_essential} for c in cats]


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics/cash-flow")
async def get_cash_flow(
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    db: AsyncSession = Depends(get_db),
):
    from_d = date(year, month, 1)
    to_d = date(year, month + 1 if month < 12 else 1, 1) if month < 12 else date(year + 1, 1, 1)

    result = await db.execute(
        select(Transaction).where(
            and_(Transaction.date >= from_d, Transaction.date < to_d)
        )
    )
    txns = result.scalars().all()
    cf = calculate_cash_flow(list(txns))

    return {
        "period": f"{year}-{month:02d}",
        "income": str(cf.income),
        "expenses": str(cf.expenses),
        "savings": str(cf.savings),
        "savings_rate": str(cf.savings_rate) if cf.savings_rate else None,
        "investment_contributions": str(cf.investment_contributions),
        "transfers": str(cf.transfers),
        "debt_payments": str(cf.debt_payments),
        "transaction_count": cf.transaction_count,
    }


@router.get("/analytics/net-worth")
async def get_net_worth(db: AsyncSession = Depends(get_db)):
    acc_result = await db.execute(select(Account).where(Account.is_active == True))
    accounts = acc_result.scalars().all()

    # Get portfolio value from investment transactions + market prices
    from app.services.ai.tools.financial_tools import _get_portfolio_value
    portfolio_value = await _get_portfolio_value(db)
    nw = calculate_net_worth(list(accounts), portfolio_value)

    return {
        "net_worth": str(nw.net_worth),
        "total_assets": str(nw.total_assets),
        "total_liabilities": str(nw.total_liabilities),
        "cash_and_bank": str(nw.cash_and_bank),
        "investment_value": str(nw.investment_value),
        "loan_outstanding": str(nw.loan_outstanding),
        "credit_card_outstanding": str(nw.credit_card_outstanding),
        "liquid_savings": str(nw.liquid_savings),
        "portfolio_value": str(portfolio_value),
    }


@router.get("/analytics/net-worth/history")
async def get_net_worth_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date))
    snapshots = result.scalars().all()
    return [
        {"date": str(s.snapshot_date), "net_worth": str(s.net_worth),
         "total_assets": str(s.total_assets), "total_liabilities": str(s.total_liabilities)}
        for s in snapshots
    ]


@router.get("/analytics/spending")
async def get_spending(
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    db: AsyncSession = Depends(get_db),
):
    from_date = date(year - 1, month, 1)
    result = await db.execute(
        select(Transaction).where(Transaction.date >= from_date)
        .options(selectinload(Transaction.category_rel))
    )
    txns = result.scalars().all()

    analysis = analyze_spending(list(txns), year, month)

    return {
        "period": f"{year}-{month:02d}",
        "total_spending": str(analysis.total_spending),
        "categories": [
            {
                "category": c.category,
                "current_month": str(c.current_month),
                "avg_3m": str(c.avg_3m) if c.avg_3m else None,
                "avg_6m": str(c.avg_6m) if c.avg_6m else None,
                "mom_change": str(c.mom_change) if c.mom_change else None,
                "mom_change_pct": str(c.mom_change_pct) if c.mom_change_pct else None,
                "is_anomaly": c.is_anomaly,
                "anomaly_reason": c.anomaly_reason,
            }
            for c in analysis.categories
            if c.current_month > 0
        ],
        "largest_transactions": analysis.largest_transactions,
        "recurring_merchants": analysis.recurring_merchants[:10],
        "spending_anomalies": analysis.spending_anomalies,
    }


@router.get("/analytics/anomalies")
async def get_anomalies(
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    db: AsyncSession = Depends(get_db),
):
    from_date = date(year - 1, month, 1)
    result = await db.execute(select(Transaction).where(Transaction.date >= from_date))
    txns = result.scalars().all()
    anomalies = detect_all_anomalies(list(txns), year, month)
    return {
        "count": len(anomalies),
        "anomalies": [
            {
                "type": a.anomaly_type,
                "severity": a.severity,
                "description": a.description,
                "entity_id": a.entity_id,
                "date": str(a.detected_on) if a.detected_on else None,
            }
            for a in anomalies
        ],
    }


# ─── Portfolio ────────────────────────────────────────────────────────────────

@router.get("/portfolio/summary")
async def portfolio_summary(db: AsyncSession = Depends(get_db)):
    from app.services.ai.tools.financial_tools import get_portfolio_summary, _load_market_prices
    result = await get_portfolio_summary(db)

    # Add data source label
    result["market_data_source"] = get_settings().market_data_source
    return result


@router.get("/portfolio/holdings")
async def portfolio_holdings(db: AsyncSession = Depends(get_db)):
    from app.services.ai.tools.financial_tools import get_holdings
    return await get_holdings(db)


@router.get("/portfolio/allocation")
async def portfolio_allocation(db: AsyncSession = Depends(get_db)):
    from app.services.ai.tools.financial_tools import get_asset_allocation
    return await get_asset_allocation(db)


@router.get("/portfolio/risk")
async def portfolio_risk(db: AsyncSession = Depends(get_db)):
    from app.services.ai.tools.financial_tools import get_portfolio_risk
    return await get_portfolio_risk(db)


# ─── Securities & Prices ──────────────────────────────────────────────────────

@router.get("/securities", response_model=list[SecurityOut])
async def list_securities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Security))
    return result.scalars().all()


@router.post("/securities", response_model=SecurityOut)
async def create_security(payload: SecurityCreate, db: AsyncSession = Depends(get_db)):
    sec = Security(**payload.model_dump())
    db.add(sec)
    await db.commit()
    await db.refresh(sec)
    return sec


@router.post("/securities/{security_id}/prices")
async def update_price(
    security_id: int,
    payload: MarketPriceCreate,
    db: AsyncSession = Depends(get_db),
):
    price = MarketPrice(
        security_id=security_id,
        price_date=payload.price_date,
        price=payload.price,
        source=MarketDataSource(payload.source),
    )
    db.add(price)
    await db.commit()
    return {"status": "price_updated", "price": str(payload.price)}


# ─── Investment Transactions ──────────────────────────────────────────────────

@router.get("/investments/transactions", response_model=list[InvestmentTransactionOut])
async def list_investment_transactions(
    security_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(InvestmentTransaction).order_by(InvestmentTransaction.date.desc())
    if security_id:
        q = q.where(InvestmentTransaction.security_id == security_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/investments/transactions", response_model=InvestmentTransactionOut)
async def create_investment_transaction(
    payload: InvestmentTransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    txn = InvestmentTransaction(**payload.model_dump())
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


# ─── Goals ────────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=list[GoalOut])
async def list_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.is_active == True))
    return result.scalars().all()


@router.post("/goals", response_model=GoalOut)
async def create_goal(payload: GoalCreate, db: AsyncSession = Depends(get_db)):
    goal = Goal(**payload.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.get("/goals/analysis")
async def goals_analysis(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.is_active == True))
    goals = result.scalars().all()
    analyses = [analyze_goal(g) for g in goals]
    return {
        "goals": [
            {
                "name": a.name,
                "type": a.goal_type,
                "target": str(a.target),
                "current": str(a.current),
                "progress_pct": str(a.progress_pct),
                "remaining": str(a.remaining),
                "months_remaining": a.months_remaining,
                "projected_value": str(a.projected_value) if a.projected_value else None,
                "required_monthly": str(a.required_monthly) if a.required_monthly else None,
                "on_track": a.on_track,
                "shortfall": str(a.shortfall) if a.shortfall else None,
            }
            for a in analyses
        ]
    }


# ─── Reports ──────────────────────────────────────────────────────────────────

@router.get("/reports/monthly")
async def monthly_report(
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    db: AsyncSession = Depends(get_db),
):
    """Structured monthly financial review."""
    from app.services.ai.tools.financial_tools import (
        get_financial_summary, get_spending_analysis, get_anomalies as _get_anomalies,
        get_goal_progress,
    )

    summary = await get_financial_summary(db, year, month)
    spending = await get_spending_analysis(db, year, month)
    anomalies = await _get_anomalies(db, year, month)
    goals = await get_goal_progress(db)
    portfolio = await portfolio_summary(db)

    return {
        "period": f"{year}-{month:02d}",
        "summary": summary,
        "spending": spending,
        "anomalies": anomalies,
        "goals": goals,
        "portfolio": portfolio,
    }


# ─── CSV Import ───────────────────────────────────────────────────────────────

@router.post("/import/csv", response_model=CSVImportResult)
async def import_csv(
    account_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    # Size check
    content = await file.read()
    if len(content) > settings.csv_max_size_bytes:
        raise HTTPException(413, f"File too large. Max {settings.csv_max_size_bytes} bytes.")

    # Get existing fingerprints for dedup
    existing = await db.execute(
        select(Transaction.date, Transaction.amount, Transaction.description)
        .where(Transaction.account_id == account_id)
    )
    fps = {
        f"{r.date}|{r.amount}|{r.description[:40]}"
        for r in existing.all()
    }

    # Parse — treat file content as potential DATA, not instructions
    text = content.decode("utf-8", errors="replace")
    parse_result = parse_bank_csv(text, fps)

    # Persist valid rows
    imported = 0
    for row in parse_result.valid:
        merchant = normalize_merchant(row.merchant or row.description)
        cat_name = categorize_transaction(row.description, merchant, float(row.amount))

        # Look up category
        cat_result = await db.execute(select(Category).where(Category.name == cat_name))
        cat = cat_result.scalar_one_or_none()

        txn_type = TransactionType.EXPENSE if row.is_debit else TransactionType.INCOME

        txn = Transaction(
            date=row.date,
            account_id=account_id,
            amount=row.amount,
            description=row.description,
            merchant=merchant,
            category_id=cat.id if cat else None,
            transaction_type=txn_type,
            reference=row.reference,
        )
        db.add(txn)
        imported += 1

    await db.commit()

    return CSVImportResult(
        imported_count=imported,
        invalid_count=len(parse_result.invalid),
        duplicate_candidates=len(parse_result.duplicate_candidates),
        warnings=parse_result.warnings,
        errors=parse_result.errors,
        invalid_rows=parse_result.invalid[:20],
    )


# ─── AI Assistant ─────────────────────────────────────────────────────────────

@router.post("/assistant/query", response_model=AssistantResponse)
async def assistant_query(
    payload: AssistantQuery,
    db: AsyncSession = Depends(get_db),
):
    # Sanitize: treat message as user query, not instructions
    question = payload.message.strip()
    if len(question) < 3:
        raise HTTPException(400, "Question too short.")

    result = await run_financial_agent(
        question=question,
        db=db,
        year=payload.year,
        month=payload.month,
    )

    return AssistantResponse(
        summary=result.get("summary", ""),
        evidence=result.get("evidence", []),
        drivers=result.get("drivers", []),
        watch_items=result.get("watch_items", []),
        confidence=result.get("confidence", "LOW"),
        confidence_reason=result.get("confidence_reason", ""),
        tools_called=result.get("tools_called", []),
        structured_data=result.get("structured_data", {}),
        error=result.get("error"),
    )


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """All data needed for the dashboard in a single call."""
    today = date.today()
    year, month = today.year, today.month

    from app.services.ai.tools.financial_tools import (
        get_financial_summary, get_spending_analysis,
        get_anomalies as _anoms, get_goal_progress,
    )

    summary = await get_financial_summary(db, year, month)
    spending = await get_spending_analysis(db, year, month)
    anomalies = await _anoms(db, year, month)
    goals = await get_goal_progress(db)
    nw_history = await get_net_worth_history(db)

    return {
        "summary": summary,
        "top_spending_categories": spending["categories"][:5],
        "anomaly_count": anomalies["anomaly_count"],
        "recent_anomalies": anomalies["anomalies"][:3],
        "goals": goals["goals"],
        "net_worth_history": nw_history[-6:],  # Last 6 months
        "market_data_source": get_settings().market_data_source,
    }


# ─── AngelOne Integration ─────────────────────────────────────────────────────

@router.post("/integrations/angelone/connect")
async def angelone_connect():
    """Test AngelOne connection using credentials from .env."""
    from app.services.integrations.angelone.angelone_service import get_angelone_service
    svc = get_angelone_service()
    try:
        profile = await svc.connect()
        return {"status": "connected", "profile": profile}
    except EnvironmentError as e:
        raise HTTPException(422, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(502, detail=f"AngelOne login failed: {e}")


@router.post("/integrations/angelone/sync")
async def angelone_sync(db: AsyncSession = Depends(get_db)):
    """Trigger a full AngelOne data sync."""
    from app.services.integrations.angelone.angelone_service import get_angelone_service
    svc = get_angelone_service()
    try:
        result = await svc.sync_to_db(db)
        if result.get("skipped"):
            return {
                "status": "skipped",
                "reason": result.get("reason"),
                "message": "Set ANGELONE_* credentials in backend/.env to enable live sync.",
            }
        return {"status": "synced", **result}
    except Exception as e:
        raise HTTPException(502, detail=f"Sync failed: {e}")


@router.get("/integrations/angelone/status")
async def angelone_status():
    """Return last sync status and connection health."""
    from app.services.integrations.angelone.angelone_service import get_sync_status, get_angelone_service
    svc = get_angelone_service()
    state = get_sync_status()
    return {"credentials_configured": svc._has_credentials, **state}
