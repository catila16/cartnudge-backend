import asyncio
from datetime import datetime, timezone
import json
from app.core.database import SessionLocal, engine, Base
from app.models.conversation import Conversation, ConversationStatus
from app.models.store import StoreSettings

async def seed_fake_cart():
    # Tabloların var olduğundan emin ol
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    db = SessionLocal()
    try:
        # 1. Fake Mağaza Ayarları
        store_domain = "test.myshopify.com"
        store = db.query(StoreSettings).filter_by(shop=store_domain).first()
        if not store:
            store = StoreSettings(
                shop=store_domain,
                is_active=True,
                maxDiscountMargin=15,
                aiPersonaTone="Samimi, espirili ve ikna edici",
                country_code="TR"
            )
            db.add(store)
            db.commit()

        # 2. Fake Terk Edilmiş Sepet (Kullanıcının Numarasıyla)
        phone = "905345900476"
        
        # Eski kayıtları temizle
        db.query(Conversation).filter_by(customer_phone=phone).delete()
        db.commit()
        
        fake_cart = {
            "token": "fake_cart_123",
            "line_items": [
                {
                    "title": "Premium Deri Ceket",
                    "price": "2500.00",
                    "quantity": 1
                },
                {
                    "title": "Güneş Gözlüğü",
                    "price": "450.00",
                    "quantity": 1
                }
            ]
        }
        
        import uuid
        conv = Conversation(
            id=str(uuid.uuid4()),
            store_id=store_domain,
            customer_phone=phone,
            cart_data=fake_cart,
            status=ConversationStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            chat_history=[]
        )
        db.add(conv)
        db.commit()
        
        print("✅ Sahte sepet başarıyla oluşturuldu! Şimdi WhatsApp'tan mesaj atabilirsiniz.")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(seed_fake_cart())
