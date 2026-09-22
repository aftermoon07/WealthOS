# 💰 WealthOS

**A privacy-first, AI-powered personal finance tracker and portfolio analysis system.**

WealthOS isn't just another expense tracker — it's your **Personal CFO and Portfolio Analyst**. It ingests your financial data, computes exact metrics (XIRR, Savings Rate, Net Worth) with deterministic Python code, and lets an AI agent interpret those *verified* numbers to answer natural-language questions about your finances — without ever hallucinating the math.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Frontend-Next.js%2015-000000?style=flat-square&logo=next.js&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white">
  <img alt="AI" src="https://img.shields.io/badge/AI-Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/status-in%20development-yellow?style=flat-square">
</p>

---

## ✨ Why WealthOS?

Most finance apps make you choose between **accuracy** and **intelligence** — a spreadsheet gets the math right but can't talk to you; a chatbot can talk but gets the math wrong. WealthOS solves this with a **"Grounded AI"** design:

> All financial math — XIRR, cost basis, P&L, savings rate — is computed by tested, deterministic Python code. The AI *never* calculates numbers itself. It only interprets results that have already been verified.

## 🚀 Core Features

| Feature | Description |
|---|---|
| 🧮 **Deterministic Financial Engine** | Exact computation of cash flows, net worth, portfolio XIRR (Newton–Raphson), and asset allocation. |
| 🤖 **Grounded AI Agent** | An LLM (Gemini) reasons over structured, pre-computed metrics — no hallucinated numbers. |
| 🔒 **Privacy First** | Local-first architecture on SQLite. Your financial data never leaves your machine. |
| 📊 **Anomaly Detection** | Flags unusual spending against historical rolling averages. |
| 🔌 **Comprehensive REST API** | A full FastAPI backend powers the entire system, ready to plug into any frontend. |

## 🏗️ How It Works

```
CSV / Manual Entry
       │
       ▼
 Ingestion Layer        →  parses HDFC / ICICI / generic bank formats
       │
       ▼
 Validation Layer       →  de-duplication, amount & date validation
       │
       ▼
 SQLite / PostgreSQL    →  Accounts, Transactions, Investments, Goals
       │
       ▼
 Deterministic Engine   →  XIRR, Net Worth, Cash Flow, Spending Analysis
       │
       ▼
 AI Tool Layer          →  wraps verified results as structured JSON
       │
       ▼
 Gemini Agent           →  answers your questions using ONLY that JSON
```

For the full breakdown, see [`ARCHITECTURE.md`](./ARCHITECTURE.md) and [`AI.md`](./AI.md).

## 📁 Project Structure

```
WealthOS/
├── backend/          # FastAPI app — domain logic, SQLite DB, REST API
├── frontend/          # Next.js 15 app — dashboard & visualizations
├── ARCHITECTURE.md    # System design and data flow
├── AI.md              # Grounded AI / tool-calling approach
└── RULES.md           # Financial correctness rules (transfers, dividends, etc.)
```

## 🛠️ Quickstart

### Prerequisites

- Python 3.9+
- Node.js 20+
- A [Gemini API key](https://ai.google.dev/) (for AI features)

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite pydantic-settings httpx

# Set your Gemini API key
export GEMINI_API_KEY="your-api-key"

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Seed demo data (optional but recommended)

Load a rich, 12-month synthetic transaction history to explore the app right away:

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Then open **[http://localhost:3000](http://localhost:3000)** to view the dashboard. 🎉

## 📚 Documentation

- 🏛️ [**Architecture**](./ARCHITECTURE.md) — system design, data flow, and modules
- 🧠 [**AI Grounding Approach**](./AI.md) — how the AI stays accurate
- 📏 [**Project Rules**](./RULES.md) — financial correctness rules

## 🗺️ Roadmap

- [ ] Multi-currency support
- [ ] PostgreSQL production deployment
- [ ] Additional bank CSV formats
- [ ] Mobile-friendly dashboard

## 🤝 Contributing

This project is in active development. Issues and pull requests are welcome — check the [Issues tab](../../issues) to get started.

## 📄 License

_No license specified yet — add one (e.g. MIT) if you plan to open this up for contributions._

---

<p align="center">Built with ❤️ by <a href="https://github.com/aftermoon07">@aftermoon07</a></p>
