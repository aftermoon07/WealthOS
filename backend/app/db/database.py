"""SQLAlchemy async engine + session factory."""
from __future__ import annotations
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


async def get_db() -> AsyncSession:  # type: ignore[override]
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup (dev/SQLite mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
