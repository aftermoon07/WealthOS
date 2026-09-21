"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db, AsyncSessionLocal
from app.api.routes.routes import router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def _angelone_sync_loop(interval_seconds: int) -> None:
    """
    Background task: syncs AngelOne data every `interval_seconds`.
    Gracefully skips if credentials are not configured or if sync fails.
    """
    from app.services.integrations.angelone.angelone_service import get_angelone_service

    # Initial delay so the server is fully started before first sync attempt
    await asyncio.sleep(5)

    svc = get_angelone_service()

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await svc.sync_to_db(db)
                if result.get("skipped"):
                    logger.info(
                        "AngelOne auto-sync skipped: %s. "
                        "Set ANGEL_API_KEY, etc. in .env to enable live data.",
                        result.get("reason", "unknown"),
                    )
                else:
                    logger.info(
                        "AngelOne auto-sync OK: %d holdings, %d trades",
                        result.get("holdings_synced", 0),
                        result.get("trades_synced", 0),
                    )
        except Exception as e:
            logger.warning("AngelOne auto-sync failed (will retry in %ds): %s", interval_seconds, e)

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (SQLite dev mode)
    await init_db()

    # Start AngelOne background sync task
    settings = get_settings()
    task = asyncio.create_task(
        _angelone_sync_loop(settings.angel_sync_interval_seconds)
    )

    yield

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="WealthOS",
    description="Privacy-first AI-powered personal finance tracker and portfolio analysis system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "WealthOS",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
