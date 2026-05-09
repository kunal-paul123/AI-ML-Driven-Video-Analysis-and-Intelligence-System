from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Async Engine — Neon DB (PostgreSQL via asyncpg)
# Neon requires SSL; it's already embedded in your DATABASE_URL (?sslmode=require)
# ─────────────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,          # Log all SQL queries in DEBUG mode
    pool_size=5,                  # Neon free tier has connection limits
    max_overflow=10,
    pool_recycle=300,             # Recycle connections every 5 min (Neon idle timeout)
    pool_pre_ping=True,           # Verify connections before use
    connect_args={"ssl": "require"},  # asyncpg needs SSL passed here, NOT in URL
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base class for all SQLAlchemy ORM models
# ─────────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Dependency — yields a DB session per request
# Usage: async def route(db: AsyncSession = Depends(get_db)):
# ─────────────────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
