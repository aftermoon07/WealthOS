from typing import AsyncGenerator
"""SQLAlchemy async engine + session factory."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    url = settings.database_url
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(url, echo=False, future=True, **kwargs)


engine = _make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
# Alias for background tasks that need their own session context
AsyncSessionLocal = SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:  # type: ignore[override]
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup (dev/SQLite mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    import os

    from app.models.models import Account
    async with SessionLocal() as session:
        result = await session.execute(select(Account))
        if not result.scalars().first():
            # If on Render or running in DEMO mode, auto-seed the database
            from app.core.config import get_settings
            settings = get_settings()
            if os.environ.get("RENDER") or settings.market_data_source == "DEMO":
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Empty database detected. Seeding demo data...")
                from app.services.ingestion.demo_seeder import seed_demo_data
                await seed_demo_data(session, force=False)
            else:
                default_acc = Account(
                    name="Default Checking",
                    account_type="CHECKING",
                    currency="INR"
                )
                session.add(default_acc)
                await session.commit()
