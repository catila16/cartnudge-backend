from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Form, BackgroundTasks, Response
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationStatus
from app.models.store import StoreSettings
from app.services.openai_service import openai_service
from app.services.twilio_service import twilio_service

router = APIRouter()
logger = logging.getLogger(__name__)

def process_whatsapp_message(from_number: str, body: str):
    """
    Background task to process the incoming WhatsApp message using OpenAI.
    """
    db: Session = SessionLocal()
    try:
        clean_phone = from_number.replace("whatsapp:", "").strip()
        
        # 1. Açık olan sepet sohbetini bul (En sonuncuyu al)
        conversation = db.query(Conversation).filter(
            Conversation.customer_phone.like(f"%{clean_phone[-10:]}"),
            Conversation.status.in_([ConversationStatus.PENDING, ConversationStatus.NEGOTIATION])
        ).order_by(Conversation.scheduled_at.desc()).first()

        if not conversation:
            logger.warning(f"No active conversation found for {from_number}")
            return

        now = datetime.now(timezone.utc)

        # 2. 24 Saatlik Pencere Kontrolü (Meta Rule)
        if conversation.last_customer_message_at:
            last_msg_time = conversation.last_customer_message_at
            if last_msg_time.tzinfo is None:
                last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
                
            elapsed = now - last_msg_time
            if elapsed > timedelta(hours=24):
                logger.warning("[Meta Violation Guard] 24 saatlik müşteri penceresi kapandı. Serbest mesaj engellendi.")
                return

        # 3. Müşterinin mesajını ve zaman damgasını kaydet
        conversation.last_customer_message_at = now
        conversation.status = ConversationStatus.NEGOTIATION
        
        history = conversation.chat_history
        if not isinstance(history, list):
            history = []
        
        # 4. Mağaza Ayarlarını Al
        store = db.query(StoreSettings).filter(StoreSettings.shop == conversation.store_id).first()
        discount_pct = store.maxDiscountMargin if store and store.maxDiscountMargin else 10
        tone = store.aiPersonaTone if store and store.aiPersonaTone else "friendly"

        # 5. OpenAI (veya Mock) Yanıtı Üret
        cart_items = []
        if isinstance(conversation.cart_data, dict):
            cart_items = conversation.cart_data.get("line_items", [])
            
        cart_url = f"https://{conversation.store_id}/cart"
        
        ai_reply = openai_service.process_negotiation_reply(
            customer_name="Değerli Müşterimiz",
            cart_items=cart_items,
            cart_url=cart_url,
            discount_percentage=discount_pct,
            tone=tone,
            chat_history=history,
            latest_message=body
        )

        # 6. Sohbet Geçmişini Güncelle
        history.append({"role": "user", "content": body})
        history.append({"role": "assistant", "content": ai_reply})
        conversation.chat_history = history
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(conversation, "chat_history")
        
        db.commit()

        # 7. Yanıtı Twilio Üzerinden API İle Gönder
        twilio_service.send_whatsapp_message(from_number, ai_reply)

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/incoming")
async def receive_whatsapp_reply(
    request: Request,
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...)
):
    """
    Webhook endpoint that Twilio/Meta hits when a user replies on WhatsApp.
    """
    logger.info(f"Incoming WhatsApp message from {From}: {Body}")
    background_tasks.add_task(process_whatsapp_message, From, Body)
    return Response(content="<Response></Response>", media_type="application/xml")
