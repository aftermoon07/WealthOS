# WealthOS

A privacy-first, AI-powered personal finance tracker and portfolio analysis system.

Unlike generic expense trackers, WealthOS acts as your Personal CFO and Portfolio Analyst. It ingests data, computes highly accurate financial metrics (XIRR, Savings Rate, Net Worth), and allows an AI agent to interpret those deterministic metrics to answer natural-language questions about your financial health.

## Core Features
- **Deterministic Financial Engine**: Computes cash flows, net worth, portfolio XIRR, and asset allocation exactly.
- **Grounded AI**: The LLM analyzes structured metrics; it never hallucinates financial math.
- **Privacy First**: Local-first architecture (SQLite). Your financial data never leaves your machine.
- **Anomaly Detection**: Flags unusual spending patterns based on historical rolling averages.
- **Comprehensive API**: A full REST API powering the entire system.

## Project Structure
- `/backend`: FastAPI Python application containing the domain logic, SQLite database, and API routes.
- `/frontend`: Next.js 15 web application for visualizing the data.
- `/docs`: See `ARCHITECTURE.md`, `AI.md`, and `RULES.md` for in-depth technical details.

## Quickstart

### Prerequisites
- Python 3.9+
- Node.js 20+
- Gemini API Key (for the AI features)

### Backend Setup
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

### Seed Demo Data
To test the system with a rich 12-month transaction dataset:
```bash
curl -X POST http://localhost:8000/api/demo/seed
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to view the dashboard.

## Documentation
- [Architecture Details](ARCHITECTURE.md)
- [AI Grounding Approach](AI.md)
- [Project Rules](RULES.md)
