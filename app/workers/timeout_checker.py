import time
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationStatus

logger = logging.getLogger(__name__)

def check_human_timeouts():
    """
    Finds conversations in HUMAN_ACTIVE state where 
    the last activity was more than 15 minutes ago,
    and reverts them back to NEGOTIATION.
    """
    db: Session = SessionLocal()
    try:
        timeout_threshold = datetime.now() - timedelta(minutes=15)
        
        timed_out_convs = db.query(Conversation).filter(
            Conversation.status == ConversationStatus.HUMAN_ACTIVE,
            Conversation.last_human_activity_at <= timeout_threshold
        ).all()
        
        for conv in timed_out_convs:
            conv.status = ConversationStatus.NEGOTIATION
            logger.info(f"[TIMEOUT] Conversation {conv.id} reverted to AI (NEGOTIATION) due to 15m inactivity.")
            
        if timed_out_convs:
            db.commit()
            
    except Exception as e:
        logger.error(f"Error checking timeouts: {e}")
        db.rollback()
    finally:
        db.close()

# If running as a standalone script for testing
if __name__ == "__main__":
    print("Running timeout checker...")
    check_human_timeouts()
    print("Done.")
