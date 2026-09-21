"""
AI FINANCIAL ANALYST AGENT
============================
The agent receives a user question, selects relevant tools,
retrieves structured data, and asks the LLM to interpret it.

Hallucination controls (see AI.md):
1. The LLM never has direct DB access.
2. All numbers come from the deterministic engine.
3. Structured tool outputs are passed as grounding context.
4. System prompt forbids invention of data.
5. Missing data is surfaced explicitly — never becomes 0.
6. Confidence is passed from the financial engine, not LLM-generated.

Response format: structured JSON.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.ai.tools.financial_tools import (
    get_financial_summary,
    get_spending_analysis,
    get_portfolio_summary,
    get_holdings,
    get_asset_allocation,
    get_portfolio_risk,
    get_anomalies,
    get_goal_progress,
    get_monthly_comparison,
    get_net_worth_history,
)


SYSTEM_PROMPT = """You are a private, precise AI financial analyst for a personal finance application.

RULES (strictly follow all):
1. NEVER invent, assume, or fabricate financial numbers, transactions, returns, or holdings.
2. ALL numbers you reference must come from the structured data provided in your context.
3. If data is unavailable or incomplete, clearly say so: "I don't have enough data to answer that reliably."
4. NEVER claim certainty about investment returns or future values.
5. NEVER recommend specific securities to buy or sell.
6. Use factual, measured language. Do NOT use alarming language for minor anomalies.
7. Present information to help the user make informed decisions — do NOT make decisions for them.
8. When confidence is marked LOW or MEDIUM, acknowledge the limitation in your response.

RESPONSE FORMAT:
Always respond with valid JSON in this exact structure:
{
  "summary": "2-3 sentence direct answer",
  "evidence": ["factual data point 1", "factual data point 2"],
  "drivers": ["key driver 1", "key driver 2"],
  "watch_items": ["thing to monitor 1"],
  "confidence": "HIGH|MEDIUM|LOW",
  "confidence_reason": "why this confidence level"
}

If you cannot answer reliably:
{
  "summary": "I don't have enough data to answer that reliably.",
  "evidence": [],
  "drivers": [],
  "watch_items": ["What data would help: ..."],
  "confidence": "LOW",
  "confidence_reason": "Insufficient data"
}"""


# ─── Intent → Tool Mapping ────────────────────────────────────────────────────


def _select_tools(question: str) -> list[str]:
    """
    Simple keyword-based tool selection.
    Returns list of tool names to call.
    Gemini/Claude can enhance this later with function calling.
    """
    q = question.lower()
    tools = []

    if any(k in q for k in ["spending", "expense", "spent", "cost", "dining", "groceries", "category"]):
        tools.append("spending_analysis")

    if any(k in q for k in ["portfolio", "investment", "stock", "mutual fund", "return", "xirr", "performance"]):
        tools.append("portfolio_summary")

    if any(k in q for k in ["holding", "position", "stock i own", "allocation breakdown"]):
        tools.append("holdings")

    if any(k in q for k in ["allocation", "diversif", "sector", "asset class"]):
        tools.append("asset_allocation")

    if any(k in q for k in ["risk", "concentration", "danger", "exposure"]):
        tools.append("portfolio_risk")

    if any(k in q for k in ["net worth", "wealth", "asset", "liabilit"]):
        tools.append("financial_summary")
        tools.append("net_worth_history")

    if any(k in q for k in ["anomal", "unusual", "suspicious", "review", "flag"]):
        tools.append("anomalies")

    if any(k in q for k in ["goal", "emergency fund", "target", "save for"]):
        tools.append("goal_progress")

    if any(k in q for k in ["compared", "last month", "previous month", "changed", "difference"]):
        tools.append("monthly_comparison")

    if any(k in q for k in ["income", "salary", "earn", "savings rate", "saving"]):
        tools.append("financial_summary")

    # Always include financial summary as baseline if nothing else matched
    if not tools:
        tools.append("financial_summary")

    return list(dict.fromkeys(tools))  # Deduplicate preserving order


# ─── Tool Executor ────────────────────────────────────────────────────────────


async def _execute_tools(
    tool_names: list[str],
    db: AsyncSession,
    year: Optional[int],
    month: Optional[int],
) -> dict:
    """Execute selected tools and return combined context."""
    context = {}
    today = date.today()
    year = year or today.year
    month = month or today.month

    for tool in tool_names:
        try:
            if tool == "financial_summary":
                context["financial_summary"] = await get_financial_summary(db, year, month)
            elif tool == "spending_analysis":
                context["spending_analysis"] = await get_spending_analysis(db, year, month)
            elif tool == "portfolio_summary":
                context["portfolio_summary"] = await get_portfolio_summary(db)
            elif tool == "holdings":
                context["holdings"] = await get_holdings(db)
            elif tool == "asset_allocation":
                context["asset_allocation"] = await get_asset_allocation(db)
            elif tool == "portfolio_risk":
                context["portfolio_risk"] = await get_portfolio_risk(db)
            elif tool == "anomalies":
                context["anomalies"] = await get_anomalies(db, year, month)
            elif tool == "goal_progress":
                context["goal_progress"] = await get_goal_progress(db)
            elif tool == "monthly_comparison":
                context["monthly_comparison"] = await get_monthly_comparison(db, year, month)
            elif tool == "net_worth_history":
                context["net_worth_history"] = await get_net_worth_history(db)
        except Exception as e:
            context[f"{tool}_error"] = str(e)

    return context


# ─── Agent Entry Point ────────────────────────────────────────────────────────


async def run_financial_agent(
    question: str,
    db: AsyncSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """
    Main agent function.
    1. Select tools based on question.
    2. Execute tools to get structured data.
    3. Send data + question to LLM.
    4. Return structured response.
    """
    settings = get_settings()

    # Step 1: Select tools
    tool_names = _select_tools(question)

    # Step 2: Execute tools
    context = await _execute_tools(tool_names, db, year, month)

    # If no API key, return data only
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        return {
            "summary": "AI analysis requires a Gemini API key. The structured data below contains your financial information.",
            "evidence": [],
            "drivers": [],
            "watch_items": ["Configure GEMINI_API_KEY in your .env file to enable AI analysis."],
            "confidence": "N/A",
            "confidence_reason": "No AI model configured",
            "structured_data": context,
            "tools_called": tool_names,
        }

    # Step 3: Build LLM prompt
    context_str = json.dumps(context, indent=2, default=str)
    user_message = f"""Question: {question}

Structured financial data retrieved from the deterministic engine:
{context_str}

Answer the question using ONLY the data above. Follow the JSON response format exactly."""

    try:
        # Direct Gemini REST API call — no SDK dependency
        api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
        }
        import asyncio
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(3):
                resp = await client.post(api_url, json=payload)
                if resp.status_code in [503, 429]:
                    await asyncio.sleep(2)
                    continue
                resp.raise_for_status()
                break
            data = resp.json()

        if "candidates" not in data:
            raise ValueError(f"Unexpected API response: {data}")

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            parsed = json.loads(json_match.group())
            parsed["tools_called"] = tool_names
            parsed["structured_data"] = context
            return parsed
        else:
            return {
                "summary": raw_text[:500],
                "evidence": [],
                "drivers": [],
                "watch_items": [],
                "confidence": "LOW",
                "confidence_reason": "Response format unexpected",
                "tools_called": tool_names,
                "structured_data": context,
            }

    except Exception as e:
        return {
            "summary": f"AI analysis temporarily unavailable: {str(e)[:200]}",
            "evidence": [],
            "drivers": [],
            "watch_items": [],
            "confidence": "LOW",
            "confidence_reason": "AI model error",
            "tools_called": tool_names,
            "structured_data": context,
            "error": str(e),
        }
