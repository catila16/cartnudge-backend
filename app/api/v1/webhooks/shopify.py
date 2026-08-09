from fastapi import APIRouter, Request, BackgroundTasks
from app.workers.cart_scheduler import schedule_cart_recovery

router = APIRouter()

# Simple in-memory cache for idempotency during local development
from cachetools import TTLCache
_scheduled_checkouts = TTLCache(maxsize=1000, ttl=3600) # 1 hour TTL

@router.post("/checkouts/update")
async def shopify_checkout_update(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Shopify checkouts/update.
    """
    payload_data = await request.json()
    checkout = payload_data.get("checkout", {})
    store_settings = payload_data.get("store_settings", {})
    
    checkout_token = checkout.get("token")
    
    # Safely cast total_price to float
    try:
        total_price = float(checkout.get("total_price", 0))
    except ValueError:
        total_price = 0.0

    min_cart_amount = store_settings.get("minCartAmount", 30)
    
    # In a real app, verify HMAC here
    
    if checkout_token:
        # Guardrail: Check Minimum Cart Amount
        if total_price < min_cart_amount:
            print(f"Checkout {checkout_token} total (${total_price}) is below minimum (${min_cart_amount}). Aborting.")
            return {"status": "ignored", "reason": "ABORTED_BELOW_MIN_CART"}

        # Idempotency check: prevent duplicate webhooks for the same checkout
        if checkout_token in _scheduled_checkouts:
            print(f"Checkout {checkout_token} is already scheduled. Ignoring duplicate webhook.")
            return {"status": "ignored", "reason": "idempotency"}
            
        _scheduled_checkouts[checkout_token] = True
        
        # We delegate the delay logic to Celery
        print(f"Checkout update received: {checkout_token}. Scheduling recovery...")
        schedule_cart_recovery(conversation_id=checkout_token, store_settings=store_settings)
        
    return {"status": "ok"}
