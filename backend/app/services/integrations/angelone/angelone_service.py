"""
AngelOne SmartAPI integration service.

Handles:
- Session management (login via TOTP + JWT)
- Fetching holdings, positions, tradebook from AngelOne
- Upserting data into local SQLite (idempotent sync)

Credentials are loaded from env vars (ANGELONE_*). If they are not set,
all public methods degrade gracefully and return empty results so the rest
of the system can continue using demo data.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import (
    Security, InvestmentTransaction, InvestmentTxnType,
    MarketPrice, MarketDataSource,
)
from .angelone_normalizer import normalize_holding, normalize_trade, normalize_position

logger = logging.getLogger(__name__)

# ── Sync State ────────────────────────────────────────────────────────────────
# In-memory state (sufficient for single-process server)
_sync_state: dict = {
    "last_sync": None,        # ISO string
    "holdings_count": 0,
    "trades_synced": 0,
    "error": None,
    "connected": False,
}


def get_sync_status() -> dict:
    return dict(_sync_state)


# ── AngelOne Service ──────────────────────────────────────────────────────────

class AngelOneService:
    """
    Wraps the SmartAPI Python SDK with async-friendly helpers.
    All network calls are run in a thread pool to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._smart = None  # lazily initialized

    @property
    def _has_credentials(self) -> bool:
        s = self._settings
        return bool(s.angel_api_key and s.angel_client_id and s.angel_password and s.angel_totp_secret)

    def _build_session(self):
        """Synchronous — runs in threadpool. Returns SmartConnect instance."""
        import pyotp
        from SmartApi import SmartConnect  # type: ignore

        s = self._settings
        totp = pyotp.TOTP(s.angel_totp_secret).now()

        smart = SmartConnect(api_key=s.angel_api_key)
        data = smart.generateSession(s.angel_client_id, s.angel_password, totp)

        if not data.get("status"):
            raise ConnectionError(f"AngelOne login failed: {data.get('message', 'unknown error')}")

        logger.info("AngelOne session established for client %s", s.angel_client_id)
        return smart, data.get("data", {})

    async def connect(self) -> dict:
        """
        Establish a session. Returns profile info dict.
        Raises ConnectionError on failure.
        """
        if not self._has_credentials:
            raise EnvironmentError(
                "AngelOne credentials not configured. "
                "Set ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET in .env"
            )
        loop = asyncio.get_event_loop()
        smart, session_data = await loop.run_in_executor(None, self._build_session)
        self._smart = smart

        profile_data = await loop.run_in_executor(None, smart.getProfile, session_data.get("refreshToken"))
        profile = profile_data.get("data", {}) if profile_data.get("status") else {}

        _sync_state["connected"] = True
        _sync_state["error"] = None
        return {
            "client_code": self._settings.angel_client_id,
            "name": profile.get("name", ""),
            "email": profile.get("email", ""),
            "broker": profile.get("broker", "ANGEL"),
            "exchanges": profile.get("exchanges", []),
        }

    async def fetch_holdings(self) -> list[dict]:
        """Fetch all demat holdings. Returns normalized list."""
        if not self._smart:
            return []
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, self._smart.allholding)
        if not resp or not resp.get("status"):
            logger.warning("allholding failed: %s", resp.get("message") if resp else "no response")
            return []

        data = resp.get("data", {})
        raw_holdings = data.get("holdings", []) if isinstance(data, dict) else []
        return [normalize_holding(h) for h in raw_holdings if h.get("tradingsymbol")]

    async def fetch_tradebook(self) -> list[dict]:
        """Fetch trade book (all executed orders). Returns normalized list."""
        if not self._smart:
            return []
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, self._smart.tradeBook)
        if not resp or not resp.get("status"):
            logger.warning("tradeBook failed: %s", resp.get("message") if resp else "no response")
            return []

        raw_trades = resp.get("data", []) or []
        normalized = [normalize_trade(t) for t in raw_trades]
        return [t for t in normalized if t is not None]

    async def fetch_positions(self) -> list[dict]:
        """Fetch open intraday/carry-forward positions."""
        if not self._smart:
            return []
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, self._smart.position)
        if not resp or not resp.get("status"):
            return []
        raw = resp.get("data", []) or []
        normalized = [normalize_position(p) for p in raw]
        return [p for p in normalized if p is not None]

    async def sync_to_db(self, db: AsyncSession) -> dict:
        """
        Full sync: fetch holdings + tradebook, upsert into SQLite.
        Returns a summary dict. Idempotent.
        """
        if not self._has_credentials:
            return {"skipped": True, "reason": "credentials_not_configured"}

        try:
            # Ensure session is active
            if not self._smart:
                await self.connect()

            holdings = await self.fetch_holdings()
            trades = await self.fetch_tradebook()

            holdings_saved = await _upsert_holdings(db, holdings)
            trades_saved = await _upsert_trades(db, trades)

            await db.commit()

            _sync_state.update({
                "last_sync": date.today().isoformat(),
                "holdings_count": holdings_saved,
                "trades_synced": trades_saved,
                "error": None,
            })

            logger.info("AngelOne sync complete: %d holdings, %d trades", holdings_saved, trades_saved)
            return {
                "holdings_synced": holdings_saved,
                "trades_synced": trades_saved,
                "last_sync": _sync_state["last_sync"],
            }

        except Exception as e:
            _sync_state["error"] = str(e)
            logger.error("AngelOne sync failed: %s", e)
            raise


# ── DB Upsert Helpers ─────────────────────────────────────────────────────────

async def _upsert_holdings(db: AsyncSession, holdings: list[dict]) -> int:
    """
    For each holding:
    1. Upsert Security (by ticker+exchange)
    2. Upsert MarketPrice (latest LTP)
    Note: We do NOT create InvestmentTransactions from holdings because
    holdings are snapshot state (quantity + avg price). Transactions come
    from the tradebook to preserve full history.
    """
    count = 0
    for h in holdings:
        ticker = h["ticker"]
        exchange = h["exchange"]

        # Upsert Security
        sec = await _get_or_create_security(db, h)

        # Upsert MarketPrice
        existing_price = await db.execute(
            select(MarketPrice).where(
                MarketPrice.security_id == sec.id,
                MarketPrice.price_date == date.today(),
            )
        )
        mp = existing_price.scalar_one_or_none()
        if mp:
            mp.price = h["ltp"]
            mp.source = MarketDataSource.API_FETCH
        else:
            mp = MarketPrice(
                security_id=sec.id,
                price_date=date.today(),
                price=h["ltp"],
                source=MarketDataSource.API_FETCH,
            )
            db.add(mp)
        count += 1

    return count


async def _upsert_trades(db: AsyncSession, trades: list[dict]) -> int:
    """
    For each normalized trade: upsert InvestmentTransaction by reference (order_id).
    Skips if already exists.
    """
    count = 0
    for t in trades:
        if not t.get("reference"):
            continue

        # Check existing by reference
        existing = await db.execute(
            select(InvestmentTransaction).where(
                InvestmentTransaction.reference == t["reference"]
            )
        )
        if existing.scalar_one_or_none():
            continue  # Already synced

        # Upsert security
        sec = await _get_or_create_security(db, {
            "ticker": t["ticker"],
            "isin": t.get("isin", ""),
            "exchange": t["exchange"],
            "investment_type": t["investment_type"],
        })

        txn_type_map = {"BUY": InvestmentTxnType.BUY, "SELL": InvestmentTxnType.SELL}
        txn_type = txn_type_map.get(t["txn_type"], InvestmentTxnType.BUY)

        inv_txn = InvestmentTransaction(
            security_id=sec.id,
            txn_type=txn_type,
            txn_date=t["txn_date"],
            quantity=t["quantity"],
            price=t["price"],
            fees=Decimal("0"),
            taxes=Decimal("0"),
            reference=t["reference"],
        )
        db.add(inv_txn)
        count += 1

    return count


async def _get_or_create_security(db: AsyncSession, h: dict) -> Security:
    """Upsert a Security record by ticker+exchange."""
    ticker = h["ticker"]
    exchange = h.get("exchange", "NSE")

    result = await db.execute(
        select(Security).where(Security.ticker == ticker, Security.exchange == exchange)
    )
    sec = result.scalar_one_or_none()

    if not sec:
        sec = Security(
            ticker=ticker,
            isin=h.get("isin") or None,
            name=ticker,  # Real name would need a separate lookup
            exchange=exchange,
            investment_type=h.get("investment_type", "STOCK"),
        )
        db.add(sec)
        await db.flush()  # Get the ID

    return sec


# ── Singleton ─────────────────────────────────────────────────────────────────

_service_instance: Optional[AngelOneService] = None


def get_angelone_service() -> AngelOneService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AngelOneService()
    return _service_instance
