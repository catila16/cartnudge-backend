import os
import hmac
import hashlib
import base64
import logging
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# The secret key for Shopify HMAC verification. 
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "dummy_secret")

async def verify_shopify_hmac(request: Request):
    """
    FastAPI Dependency to verify Shopify Webhook HMAC signatures.
    Reads the raw body and validates the signature against SHOPIFY_API_SECRET.
    Saves the raw body to request.state.raw_body to prevent stream consumption issues.
    """
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    
    if not hmac_header:
        logger.error("Missing X-Shopify-Hmac-Sha256 header")
        raise HTTPException(status_code=401, detail="Missing HMAC header")
        
    # Read raw body once and store it in request.state for downstream use
    raw_body = await request.body()
    request.state.raw_body = raw_body
    
    # Compute the SHA256 HMAC
    computed_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).digest()
    
    computed_hmac_base64 = base64.b64encode(computed_hmac).decode('utf-8')
    
    # Compare securely to prevent timing attacks
    if not hmac.compare_digest(computed_hmac_base64, hmac_header):
        logger.error(f"HMAC validation failed. Expected: {computed_hmac_base64}, Received: {hmac_header}")
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
        
    return True
