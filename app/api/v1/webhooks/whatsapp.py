from fastapi import APIRouter, Request, Form, BackgroundTasks
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationStatus
from app.services.twilio_service import send_whatsapp_message

router = APIRouter()
logger = logging.getLogger(__name__)

def process_whatsapp_message(from_number: str, body: str):
    """
    Background task to process the incoming WhatsApp message.
    """
    db: Session = SessionLocal()
    try:
        # For MVP, find conversation by phone number (in production, ensure it's active)
        conv = db.query(Conversation).filter(Conversation.customer_phone == from_number).order_by(Conversation.scheduled_at.desc()).first()
        
        if not conv:
            logger.warning(f"No conversation found for {from_number}")
            return
            
        if conv.status == ConversationStatus.HUMAN_ACTIVE:
            logger.info(f"Human is active for {from_number}. AI is muted.")
            # We don't trigger LLM. The UI would read this via logs or future SSE.
            return
            
        if conv.status in [ConversationStatus.PENDING, ConversationStatus.NEGOTIATION]:
            conv.status = ConversationStatus.NEGOTIATION
            db.commit()
            
            # Here we would call the negotiator LLM. 
            # For MVP, we simulate LLM response and dynamic discount check.
            from app.services.integrations.shopify_discount import generate_discount_url
            
            discount_url = generate_discount_url(conv.id, 10, conv.store_id)
            llm_response = f"Harika! Size özel %10 indirim kodunuzu oluşturdum. Hemen siparişinizi tamamlamak için tıklayın: {discount_url}"
            
            send_whatsapp_message(from_number, llm_response)
            
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
    We process the message asynchronously so Twilio doesn't timeout.
    """
    logger.info(f"Incoming WhatsApp message from {From}: {Body}")
    
    # Process asynchronously to immediately return 200 OK
    background_tasks.add_task(process_whatsapp_message, From, Body)
    
    return {"status": "Message received, processing in background"}
