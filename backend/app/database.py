import urllib.parse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings


def get_async_db_url(url: str) -> str:
    """Format and adjust database URL scheme and query parameters for async driver compatibility."""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    if "postgresql+asyncpg://" in url:
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        # Strip parameters unsupported by asyncpg
        query_params.pop("channel_binding", None)
        query_params.pop("sslmode", None)
        query_params["ssl"] = ["require"]
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        url = urllib.parse.urlunparse(parsed._replace(query=new_query))

    return url


db_url = get_async_db_url(settings.database_url)

# echo=False keeps logs clean; flip to True while debugging SQL
engine = create_async_engine(db_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """FastAPI dependency that yields an async DB session and always closes it."""
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
