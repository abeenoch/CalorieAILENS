from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from config import get_settings


settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight SQLite migration for additive columns used in local dev.
        # This avoids breaking existing DB files when we add new JSON fields.
        if settings.database_url.startswith("sqlite"):
            result = await conn.execute(text("PRAGMA table_info(meals)"))
            columns = {row[1] for row in result.fetchall()}
            if "agent_results" not in columns:
                await conn.execute(text("ALTER TABLE meals ADD COLUMN agent_results JSON"))
