from fastapi import APIRouter
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationStatus

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/takeover/{conversation_id}")
async def human_takeover(conversation_id: str):
    """
    Triggered by the Frontend 'Takeover' button.
    Sets conversation status to HUMAN_ACTIVE, pausing the AI.
    """
    db: Session = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conv:
            return {"status": "error", "message": "Conversation not found"}, 404
            
        conv.status = ConversationStatus.HUMAN_ACTIVE
        conv.last_human_activity_at = datetime.now()
        # Mark as assisted so if it converts, the commission is 4%
        conv.conversion_type = "ASSISTED"
        
        db.commit()
        
        logger.info(f"[TAKEOVER] Conversation {conversation_id} is now HUMAN_ACTIVE.")
        
        return {"status": "success", "message": "Human takeover active"}
        
    except Exception as e:
        logger.error(f"Error during takeover: {e}")
        db.rollback()
        return {"status": "error", "message": "Internal error"}, 500
    finally:
        db.close()
