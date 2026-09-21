import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.conversation import Conversation

async def check():
    async with SessionLocal() as session:
        result = await session.execute(select(Conversation))
        rows = result.scalars().all()
        print(f"Total conversations: {len(rows)}")
        for r in rows:
            print(f"ID: {r.id}, Phone: {r.customer_phone}, Status: {r.status}")

asyncio.run(check())
