# Finance Intelligence Engine — Architecture

## Vision

A **privacy-first, AI-powered personal finance tracker and portfolio analysis system** that runs completely locally. No data leaves your machine. The AI acts as a financial analyst that interprets structured data retrieved by a deterministic backend — it never independently calculates authoritative numbers.

## Design Principles

1. **Deterministic Calculations First** — XIRR, CAGR, P&L, cost basis, savings rate, net worth, and all financial metrics are computed by verified Python code with unit tests. The AI interprets these numbers; it does not calculate them.

2. **Grounded AI** — The LLM receives only specific JSON context retrieved by tool-layer functions. It cannot see raw database dumps, cannot execute SQL, and cannot make financial calculations itself.

3. **Financial Correctness** — Transfers between own accounts are never counted as expenses. Credit card repayments are never double-counted. Investment purchases are tracked separately from spending. Dividends are income.

4. **Privacy First** — V1 is local-only. SQLite by default. No authentication required. No cloud sync.

5. **Modular Monolith** — Not microservices. One codebase, clear module boundaries, simple deployment.

---

## System Architecture

```
Financial Data (CSV / Manual Entry)
         │
         ▼
┌────────────────────┐
│   INGESTION LAYER  │  csv_parser.py — multi-format HDFC/ICICI/Generic
│                    │  demo_seeder.py — 12-month complex demo dataset
└────────────────────┘
         │  NormalizedRow objects
         ▼
┌────────────────────┐
│  VALIDATION LAYER  │  Duplicate detection (fingerprinting)
│                    │  Amount validation, date parsing, enum guards
└────────────────────┘
         │
         ▼
┌────────────────────┐
│     DATABASE       │  SQLite (dev) / PostgreSQL (prod)
│   (SQLAlchemy 2)   │  Async sessions via aiosqlite
│                    │  Models: Account, Transaction, InvestmentTxn,
│                    │          Security, MarketPrice, Goal, NetWorthSnapshot
└────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│         DETERMINISTIC FINANCIAL ENGINE        │
│                                              │
│  cash_flow.py      — Income / Expenses / Savings / Savings Rate  │
│  net_worth.py      — Assets / Liabilities / Emergency Fund       │
│  portfolio_engine.py — XIRR (Newton-Raphson), WAVG Cost Basis,  │
│                        Unrealized/Realized P&L, CAGR             │
│  spending.py       — Category analysis, MoM trends, merchants    │
│  anomalies.py      — Threshold-based pattern detection           │
│  categorization.py — Rule-based + fallback merchant normalization│
│  goals_engine.py   — Goal progress, projections, required SIP    │
└──────────────────────────────────────────────┘
         │
         ▼
┌────────────────────┐
│   AI TOOL LAYER    │  financial_tools.py
│                    │  Controlled data retrieval functions:
│                    │  - get_financial_summary()
│                    │  - get_spending_analysis()
│                    │  - get_portfolio_summary()
│                    │  - get_holdings()
│                    │  - get_asset_allocation()
│                    │  - get_portfolio_risk()
│                    │  - get_anomalies()
│                    │  - get_goal_progress()
│                    │  - get_monthly_comparison()
│                    │  - get_net_worth_history()
└────────────────────┘
         │  Structured JSON context
         ▼
┌────────────────────┐
│     AI AGENT       │  financial_agent.py
│                    │  1. Intent classification (_select_tools)
│                    │  2. Tool execution (_execute_tools)
│                    │  3. Grounded LLM inference (Gemini REST API)
│                    │  4. Structured response (JSON)
└────────────────────┘
         │
         ▼
┌────────────────────┐
│     REST API       │  FastAPI + Uvicorn
│                    │  40+ endpoints across:
│                    │  - /api/accounts, /api/transactions
│                    │  - /api/analytics/cash-flow, net-worth, spending
│                    │  - /api/portfolio/summary, holdings, allocation
│                    │  - /api/goals, /api/import/csv
│                    │  - /api/assistant/query
│                    │  - /api/dashboard (aggregated)
│                    │  - /api/reports/monthly
└────────────────────┘
         │
         ▼
┌────────────────────┐
│  THIN FRONTEND     │  Next.js 15 + App Router
│                    │  Dashboard, Portfolio, Spending, AI Assistant
│                    │  No business logic — pure API consumer
└────────────────────┘
```

---

## Directory Structure

```
finance-intelligence-engine/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI entrypoint
│   │   ├── core/config.py               # Settings (env-based)
│   │   ├── db/database.py               # Async SQLAlchemy engine
│   │   ├── models/models.py             # ORM models
│   │   ├── schemas/schemas.py           # Pydantic request/response
│   │   ├── api/routes/routes.py         # All REST routes
│   │   └── services/
│   │       ├── domain/
│   │       │   ├── finance/             # cash_flow.py, net_worth.py
│   │       │   ├── portfolio/           # portfolio_engine.py
│   │       │   ├── analytics/           # spending.py, anomalies.py
│   │       │   ├── transactions/        # categorization.py
│   │       │   └── goals/               # goals_engine.py
│   │       ├── ai/
│   │       │   ├── tools/financial_tools.py   # Tool layer
│   │       │   ├── agent/financial_agent.py   # Agent entry point
│   │       │   └── prompts/system_prompt.py   # LLM system prompt
│   │       └── ingestion/
│   │           ├── csv_parser.py              # Multi-format CSV parser
│   │           └── demo_seeder.py             # Demo dataset
│   └── tests/
│       └── test_domain.py               # 46 domain unit tests
└── frontend/
    ├── app/                             # Next.js App Router
    ├── components/                      # UI components
    └── lib/api.ts                       # API client
```

---

## Data Models

### Account
- `account_type`: SAVINGS | CURRENT | CREDIT_CARD | LOAN | INVESTMENT | FIXED_DEPOSIT | PROVIDENT_FUND
- Tracks `outstanding_balance` for assets; `loan_principal` + `interest_rate` + `emi` for debt

### Transaction
- `transaction_type`: INCOME | EXPENSE | TRANSFER | INVESTMENT_BUY | INVESTMENT_SELL | DIVIDEND | REFUND | DEBT_PAYMENT
- `TRANSFER` and `DEBT_PAYMENT` are **excluded from expense calculations** to prevent double-counting
- `INVESTMENT_BUY`/`SELL` are tracked separately as `investment_contributions`
- `duplicate_status`: UNIQUE | DUPLICATE_CANDIDATE | CONFIRMED_DUPLICATE

### InvestmentTransaction
- `txn_type`: BUY | SELL | DIVIDEND | BONUS | SPLIT | RIGHTS
- Quantity in units (shares / NAV units), price per unit
- Fees and taxes tracked separately

### MarketPrice
- `source`: DEMO | MANUAL | API_FETCH
- Latest price per security used for portfolio valuation

---

## Financial Calculation Reference

### Cash Flow
```
Income = Σ(INCOME) + Σ(DIVIDEND) - Σ(REFUND)
Expenses = Σ(EXPENSE)  [NOT including TRANSFER, DEBT_PAYMENT, INVESTMENT_BUY]
Savings = Income - Expenses
Savings Rate = Savings / Income × 100  [None if Income = 0]
Investment Contributions = Σ(INVESTMENT_BUY)
```

### Net Worth
```
Total Assets = Σ(cash/bank balances) + portfolio_value + Σ(FD/PF)
Total Liabilities = Σ(loan_outstanding) + Σ(cc_outstanding)
Net Worth = Total Assets - Total Liabilities
Liquid Savings = Σ(SAVINGS + CURRENT balances)  [NOT investments]
Emergency Fund Coverage = Liquid Savings / Monthly Essential Expenses
```

### Portfolio (WAVG Cost Basis)
```
Average Cost = Σ(buy_qty × buy_price) / Σ(buy_qty)  [after partial sells]
Unrealized P&L = (Current Price - Average Cost) × Current Quantity
Realized P&L = Σ(sell_qty × sell_price) - Σ(sell_qty × avg_cost_at_time_of_sell)
XIRR = Newton-Raphson on: [-invest_cashflows, +portfolio_value_today]
CAGR = (End / Start)^(1/years) - 1
```

---

## AI Agent Design

### Tool Selection (Intent Classification)
The agent maps question keywords to the minimal set of tools needed:
- "spend / expense / category" → `spending_analysis`
- "portfolio / stock / return / xirr" → `portfolio_summary`
- "net worth / assets / liability" → `net_worth_history`
- "goal / target / SIP" → `goal_progress`
- "anomaly / unusual / alert" → `anomalies`

### Grounding Contract
The LLM receives a structured JSON payload:
```json
{
  "financial_summary": { "income": "...", "expenses": "...", ... },
  "portfolio_summary": { "xirr": "...", "holdings": [...], ... }
}
```
The system prompt explicitly prohibits: hallucinating numbers, calculating returns independently, providing advice not supported by data.

### Confidence Levels
- `HIGH`: All relevant data available, no missing prices, full history
- `MEDIUM`: Partial data or missing market prices
- `LOW`: Missing tools data or AI model error

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/demo/seed` | Seed 12-month demo dataset |
| GET | `/api/accounts` | List all accounts |
| POST | `/api/accounts` | Create account |
| GET | `/api/transactions` | List transactions (filterable) |
| PATCH | `/api/transactions/{id}` | Update category/description |
| GET | `/api/analytics/cash-flow` | Monthly cash flow |
| GET | `/api/analytics/net-worth` | Current net worth |
| GET | `/api/analytics/net-worth/history` | Net worth over time |
| GET | `/api/analytics/spending` | Spending breakdown + trends |
| GET | `/api/analytics/anomalies` | Detected anomalies |
| GET | `/api/portfolio/summary` | Portfolio metrics + XIRR |
| GET | `/api/portfolio/holdings` | Current holdings |
| GET | `/api/portfolio/allocation` | Asset + sector allocation |
| GET | `/api/portfolio/risk` | Risk dimensions |
| GET | `/api/goals` | All financial goals |
| POST | `/api/goals` | Create goal |
| GET | `/api/goals/analysis` | Goal projections |
| POST | `/api/import/csv` | Upload bank statement CSV |
| POST | `/api/assistant/query` | AI financial analyst query |
| GET | `/api/dashboard` | Aggregated dashboard data |
| GET | `/api/reports/monthly` | Full monthly report |

---

## Test Coverage

46 unit tests across:
- `TestCashFlow` — 10 tests including double-counting invariants
- `TestNetWorth` — 5 tests
- `TestPortfolioEngine` — 13 tests (XIRR, WAVG, P&L, allocation, concentration)
- `TestCategorization` — 7 tests
- `TestCSVParser` — 6 tests (dedup, format, invalid rows)
- `TestAnomalyDetection` — 3 tests
- `TestFinancialInvariants` — 2 invariant tests

Run: `pytest tests/ -v`

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./finance.db` | Database connection string |
| `GEMINI_API_KEY` | (required for AI) | Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | LLM model |
| `MARKET_DATA_SOURCE` | `DEMO` | Price source: DEMO / MANUAL / API_FETCH |
| `APP_ENV` | `development` | Environment |

---

## Running Locally

```bash
# Backend
cd backend
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite pydantic-settings httpx
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Seed demo data
curl -X POST http://localhost:8000/api/demo/seed

# API docs
open http://localhost:8000/docs

# Frontend
cd frontend
npm install && npm run dev
open http://localhost:3000
```
