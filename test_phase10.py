import requests
import time
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, sync_engine, Base
from app.models.conversation import Conversation, ConversationStatus
from datetime import datetime, timedelta

Base.metadata.create_all(bind=sync_engine)

def seed_db():
    db: Session = SessionLocal()
    # Delete existing test conv
    db.query(Conversation).filter(Conversation.id == "conv_test_123").delete()
    
    # Create test conversation
    conv = Conversation(
        id="conv_test_123",
        store_id="test_store.myshopify.com",
        customer_phone="+905550001122",
        cart_data={"items": ["Sneakers"]},
        status=ConversationStatus.PENDING,
        scheduled_at=datetime.now()
    )
    db.add(conv)
    db.commit()
    print("Database seeded with test conversation.")
    db.close()

seed_db()

base_url = "http://127.0.0.1:8000"

print("\n--- Test 1: Inbound WhatsApp Message (PENDING -> NEGOTIATION) ---")
res1 = requests.post(
    f"{base_url}/api/v1/webhooks/whatsapp/incoming",
    data={"From": "+905550001122", "Body": "Merhaba, indirim var mi?"}
)
print("WhatsApp Webhook Response:", res1.json())
time.sleep(2) # Give background task time to run

# Check DB
db: Session = SessionLocal()
conv = db.query(Conversation).filter(Conversation.id == "conv_test_123").first()
print(f"Conversation status after message: {conv.status.value}")
db.close()


print("\n--- Test 2: Human Takeover ---")
res2 = requests.post(f"{base_url}/api/v1/live-support/takeover/conv_test_123")
print("Takeover Response:", res2.json())

# Check DB
db = SessionLocal()
conv = db.query(Conversation).filter(Conversation.id == "conv_test_123").first()
print(f"Conversation status after takeover: {conv.status.value}")
db.close()


print("\n--- Test 3: Inbound WhatsApp while HUMAN_ACTIVE ---")
res3 = requests.post(
    f"{base_url}/api/v1/webhooks/whatsapp/incoming",
    data={"From": "+905550001122", "Body": "Orada misiniz?"}
)
print("WhatsApp Webhook Response:", res3.json())
time.sleep(1)


print("\n--- Test 4: Auto-Timeout Checker ---")
# Manually shift last_human_activity_at to 20 mins ago
db = SessionLocal()
conv = db.query(Conversation).filter(Conversation.id == "conv_test_123").first()
conv.last_human_activity_at = datetime.now() - timedelta(minutes=20)
db.commit()
db.close()

# Run the timeout checker
from app.workers.timeout_checker import check_human_timeouts
check_human_timeouts()

db = SessionLocal()
conv = db.query(Conversation).filter(Conversation.id == "conv_test_123").first()
print(f"Conversation status after timeout worker ran: {conv.status.value}")
db.close()
