# AI Grounding Architecture

The Finance Intelligence Engine uses a "Grounded AI" approach. The AI (Gemini) acts purely as an interpretation and reasoning layer on top of a deterministic financial engine.

## The Problem with LLMs in Finance
Large Language Models are notoriously bad at math. If you give an LLM a list of 500 transactions and ask it to calculate your savings rate or portfolio XIRR, it will hallucinate a number that looks plausible but is completely wrong. Financial data requires 100% precision.

## Our Solution: The Tool Layer
To solve this, we strictly separate **Calculation** from **Interpretation**.

1. **Deterministic Engine (Python)**: All math is done in Python. When a user asks "What is my XIRR?", the Python `portfolio_engine.py` runs a Newton-Raphson calculation on exact cash flows from the SQLite database.
2. **Tool Layer**: The result is wrapped into a strictly typed JSON object (e.g., `{"xirr": 20.99, "confidence": "HIGH"}`).
3. **Agent Layer**: The LLM is provided with this JSON object as its context and asked to answer the user's question using ONLY the provided data.

## Implementation Details

The AI Agent (`financial_agent.py`) operates in a multi-step loop:

1. **Intent Classification**: The user's query is analyzed to determine which tools are needed. (e.g., "Am I spending too much?" triggers `get_spending_analysis` and `get_anomalies`).
2. **Tool Execution**: The backend executes the selected Python functions to gather data from the database.
3. **Context Assembly**: The results are assembled into a JSON payload.
4. **Final Inference**: The Gemini model is called via REST API with a strict System Prompt:
   - "You are a senior financial analyst."
   - "You must base all numbers on the provided JSON context."
   - "Do not hallucinate calculations."
5. **Response Delivery**: The AI's response is returned to the user via the API.

## Tools Available to the AI
- `get_financial_summary`: Income, expenses, savings rate.
- `get_spending_analysis`: Category breakdowns, MoM trends.
- `get_portfolio_summary`: XIRR, realized/unrealized P&L.
- `get_holdings`: Detailed asset positions.
- `get_asset_allocation`: Asset classes and sectors.
- `get_portfolio_risk`: Concentration and volatility metrics.
- `get_goal_progress`: Progress towards financial targets.
- `get_net_worth_history`: Historical net worth tracking.
- `get_anomalies`: Flagged unusual spending patterns.
