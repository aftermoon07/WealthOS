"""
AngelOne SmartAPI normalizer.

Maps raw AngelOne API response fields to our internal domain models.
"""
from __future__ import annotations

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# ── Field mappings ────────────────────────────────────────────────────────────

def normalize_holding(raw: dict) -> dict:
    """
    Maps a single item from getAllHolding['data']['holdings'] to our schema.

    Returns a dict suitable for upserting a Security + MarketPrice + InvestmentTransaction.
    """
    ticker = raw.get("tradingsymbol", "").strip().upper()
    isin = raw.get("isin", "").strip()
    exchange = raw.get("exchange", "NSE").strip().upper()

    try:
        qty = Decimal(str(raw.get("quantity", 0)))
        avg_price = Decimal(str(raw.get("averageprice", 0)))
        ltp = Decimal(str(raw.get("ltp", 0)))
        pnl = Decimal(str(raw.get("profitandloss", 0)))
        pnl_pct = Decimal(str(raw.get("pnlpercentage", 0)))
        t1_qty = Decimal(str(raw.get("t1quantity", 0)))
    except Exception:
        qty = avg_price = ltp = pnl = pnl_pct = t1_qty = Decimal("0")

    product = raw.get("product", "").upper()
    symbol_token = raw.get("symboltoken", "")

    # Infer investment type
    investment_type = _infer_investment_type(ticker, exchange, product)

    return {
        "ticker": ticker,
        "isin": isin,
        "exchange": exchange,
        "symbol_token": symbol_token,
        "investment_type": investment_type,
        "quantity": qty,
        "average_price": avg_price,
        "ltp": ltp,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "t1_quantity": t1_qty,
        "product": product,
    }


def normalize_trade(raw: dict) -> Optional[dict]:
    """
    Maps a single item from getTradeBook['data'] to our InvestmentTransaction schema.

    Returns None if the trade cannot be normalized (e.g. missing critical fields).
    """
    try:
        ticker = raw.get("tradingsymbol", "").strip().upper()
        if not ticker:
            return None

        txn_type_str = raw.get("transactiontype", "").upper()
        txn_type = "BUY" if txn_type_str == "BUY" else "SELL"

        qty = Decimal(str(raw.get("quantity", 0)))
        price = Decimal(str(raw.get("price", 0) or raw.get("averageprice", 0)))
        if qty <= 0 or price <= 0:
            return None

        # Parse filltime: "18-Sep-2026 09:15:00"
        fill_time_str = raw.get("filltime", raw.get("updatetime", ""))
        txn_date = _parse_angel_datetime(fill_time_str)

        exchange = raw.get("exchange", "NSE").strip().upper()
        isin = raw.get("isin", "").strip()
        product = raw.get("producttype", raw.get("product", "")).upper()
        order_id = raw.get("orderid", "")

        investment_type = _infer_investment_type(ticker, exchange, product)

        return {
            "ticker": ticker,
            "isin": isin,
            "exchange": exchange,
            "investment_type": investment_type,
            "txn_type": txn_type,
            "quantity": qty,
            "price": price,
            "txn_date": txn_date,
            "product": product,
            "order_id": order_id,
            "reference": f"AO-{order_id}",
        }
    except Exception as e:
        logger.warning("Could not normalize trade %s: %s", raw.get("orderid", "?"), e)
        return None


def normalize_position(raw: dict) -> Optional[dict]:
    """Maps a getPosition item to a lightweight position dict."""
    try:
        ticker = raw.get("tradingsymbol", "").strip().upper()
        if not ticker:
            return None

        net_qty = Decimal(str(raw.get("netqty", 0)))
        ltp = Decimal(str(raw.get("ltp", 0)))
        buy_avg = Decimal(str(raw.get("buyavgprice", 0)))
        pnl = Decimal(str(raw.get("pnl", 0)))
        exchange = raw.get("exchange", "NSE").strip().upper()

        return {
            "ticker": ticker,
            "exchange": exchange,
            "net_qty": net_qty,
            "ltp": ltp,
            "buy_avg": buy_avg,
            "pnl": pnl,
        }
    except Exception as e:
        logger.warning("Could not normalize position %s: %s", raw.get("tradingsymbol", "?"), e)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_investment_type(ticker: str, exchange: str, product: str) -> str:
    """Heuristic to classify investment type from ticker and exchange."""
    t = ticker.upper()
    # ETFs and index funds commonly end with specific suffixes
    etf_patterns = ["BEES", "GOLDBEES", "LIQUIDBEES", "ETF", "NIFTYBEES", "BANKBEES"]
    mf_patterns = ["DIRECT", "GROWTH", "IDCW"]

    if any(p in t for p in etf_patterns):
        return "ETF"
    if any(p in t for p in mf_patterns):
        return "MUTUAL_FUND"
    if "GOLD" in t or "SGOLD" in t:
        return "GOLD"
    if exchange in ("NSE", "BSE"):
        return "STOCK"
    return "STOCK"


def _parse_angel_datetime(s: str) -> date:
    """Parse AngelOne datetime strings like '18-Sep-2026 09:15:00'."""
    if not s:
        return date.today()
    formats = [
        "%d-%b-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse AngelOne datetime: %r — using today", s)
    return date.today()
