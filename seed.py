import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.store import StoreSettings
import uuid

DATABASE_URL = 'sqlite+aiosqlite:///./cartnudge.db'
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_data():
    async with AsyncSessionLocal() as session:
        stores = [
            (str(uuid.uuid4()), 'cool-fashion.myshopify.com', 'TR', 29, 1, None, '2026-08-01 10:00:00'),
            (str(uuid.uuid4()), 'tech-gadgets-us.myshopify.com', 'US', 99, 1, None, '2026-08-05 14:30:00'),
            (str(uuid.uuid4()), 'berlin-shoes.myshopify.com', 'DE', 49, 1, None, '2026-08-10 09:15:00'),
            (str(uuid.uuid4()), 'istanbul-coffee.myshopify.com', 'TR', 49, 1, None, '2026-08-12 16:45:00'),
            (str(uuid.uuid4()), 'london-books.myshopify.com', 'GB', 29, 1, None, '2026-08-15 11:20:00')
        ]
        
        for s in stores:
            query = text(f'INSERT INTO {StoreSettings.__tablename__} (id, shop, country_code, subscription_plan_price, is_active, uninstalled_at, createdAt, updatedAt) VALUES (:id, :shop, :country, :price, :active, :uninstalled, :created, :updated)')
            try:
                await session.execute(query, {'id': s[0], 'shop': s[1], 'country': s[2], 'price': s[3], 'active': s[4], 'uninstalled': s[5], 'created': s[6], 'updated': s[6]})
            except Exception as e:
                print('Error inserting:', s[1], e)
        await session.commit()
        print('Dummy data inserted successfully.')

asyncio.run(seed_data())
