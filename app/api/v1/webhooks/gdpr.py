from fastapi import APIRouter, Request, BackgroundTasks, Depends
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation
from app.models.store import StoreSettings
from app.core.security import verify_shopify_hmac

router = APIRouter(dependencies=[Depends(verify_shopify_hmac)])
logger = logging.getLogger(__name__)

def background_customer_redact(customer_id: str, phone: str):
    """
    Background task to wipe customer data.
    """
    db: Session = SessionLocal()
    try:
        # Purge all conversations related to this customer phone
        if phone:
            db.query(Conversation).filter(Conversation.customer_phone == phone).delete()
            db.commit()
            logger.info(f"[GDPR] Wiped customer data for phone {phone}")
    except Exception as e:
        logger.error(f"[GDPR] Error redacting customer {customer_id}: {e}")
        db.rollback()
    finally:
        db.close()

def background_shop_redact(shop_domain: str):
    """
    Background task to wipe entire shop data on app uninstall.
    """
    db: Session = SessionLocal()
    try:
        # Delete store settings and all related conversations
        db.query(Conversation).filter(Conversation.store_id == shop_domain).delete()
        db.query(StoreSettings).filter(StoreSettings.shop == shop_domain).delete()
        db.commit()
        logger.info(f"[GDPR] Wiped all data for store {shop_domain}")
    except Exception as e:
        logger.error(f"[GDPR] Error redacting shop {shop_domain}: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/customers/data_request")
async def gdpr_customers_data_request(request: Request):
    """
    Called by Shopify when a customer requests to view their data.
    For MVP, we just acknowledge. Real apps might email the data.
    """
    payload = await request.json()
    logger.info(f"[GDPR] Customer data request received: {payload.get('customer', {}).get('id')}")
    return {"status": "ok"}

@router.post("/customers/redact")
async def gdpr_customers_redact(request: Request, background_tasks: BackgroundTasks):
    """
    Called by Shopify when a customer requests to delete their data.
    """
    payload = await request.json()
    customer_id = str(payload.get("customer", {}).get("id"))
    phone = payload.get("customer", {}).get("phone")
    
    logger.info(f"[GDPR] Customer redact request for ID: {customer_id}")
    
    # Delegate to background task to ensure <5s response
    background_tasks.add_task(background_customer_redact, customer_id, phone)
    
    return {"status": "processing"}

@router.post("/shop/redact")
async def gdpr_shop_redact(request: Request, background_tasks: BackgroundTasks):
    """
    Called by Shopify 48 hours after app is uninstalled.
    Must delete all shop data.
    """
    payload = await request.json()
    shop_domain = payload.get("shop_domain")
    
    logger.info(f"[GDPR] Shop redact request for: {shop_domain}")
    
    # Delegate to background task to ensure <5s response
    background_tasks.add_task(background_shop_redact, shop_domain)
    
    return {"status": "processing"}
