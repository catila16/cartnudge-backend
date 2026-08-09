import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

raw_url = os.getenv("DATABASE_URL", "sqlite:///./cartnudge.db").strip('"').strip("'")

# Ensure proper driver for async and sync engines
if raw_url.startswith("postgres://") or raw_url.startswith("postgresql://"):
    # Fix standard postgres URL for asyncpg
    DATABASE_URL = raw_url.replace("postgres://", "postgresql+asyncpg://").replace("postgresql://", "postgresql+asyncpg://")
    SYNC_DATABASE_URL = raw_url.replace("postgres://", "postgresql://")
    
    # Also fix common user typos like ":port/"
    DATABASE_URL = DATABASE_URL.replace(":port/", ":5432/")
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace(":port/", ":5432/")
    
    # Strip ?schema=public which Prisma uses but asyncpg rejects
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    if "?" in SYNC_DATABASE_URL:
        SYNC_DATABASE_URL = SYNC_DATABASE_URL.split("?")[0]
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cartnudge.db")
    SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "sqlite:///./cartnudge.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
