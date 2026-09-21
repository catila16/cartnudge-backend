import os
import secrets
import hmac
import hashlib
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.core.database import get_db
from app.models.store import StoreSettings

router = APIRouter()

# Client credentials from earlier setup
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")

# The required scopes for webhooks and API calls
SCOPES = "read_checkouts,read_orders,write_orders,read_products,read_customers"

# Fallback base URL for the app
APP_URL = os.getenv("APP_URL", "https://slick-times-eat.loca.lt")

@router.get("/install")
async def install(shop: str, db: AsyncSession = Depends(get_db)):
    """
    Initiates the OAuth flow.
    Generates a nonce (state) for CSRF protection and redirects the user to the Shopify OAuth screen.
    """
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain")

    # 1. Generate a random nonce for CSRF protection
    nonce = secrets.token_hex(16)
    
    # 2. Save the nonce in the database for this shop
    result = await db.execute(select(StoreSettings).where(StoreSettings.shop == shop))
    store = result.scalar_one_or_none()
    
    if not store:
        store = StoreSettings(shop=shop, nonce=nonce)
        db.add(store)
    else:
        store.nonce = nonce
        
    await db.commit()

    # 3. Build the OAuth Authorization URL
    # By passing `grant_options[]=per-user`, we request an online (expiring) access token.
    # Shopify no longer allows non-expiring offline tokens for new apps without Token Exchange.
    redirect_uri = f"{APP_URL}/api/v1/auth/callback"
    auth_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={SCOPES}&redirect_uri={redirect_uri}&state={nonce}&grant_options[]=per-user"
    
    # We use window.top.location.href because if the user clicks the install link from INSIDE an iframe (e.g. they clicked an app link), we need to break out to the full window.
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript">
            window.top.location.href = "{auth_url}";
        </script>
    </head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 50px;">
        <h2>Redirecting to Shopify for authentication...</h2>
        <p>If you are not redirected, <a href="{auth_url}" target="_top">click here</a>.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/callback")
async def callback(request: Request, shop: str, hmac: str, code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    The callback endpoint where Shopify sends the merchant after they approve the installation.
    Verifies the HMAC signature, validates the nonce (CSRF), and exchanges the code for a permanent access token.
    """
    # 1. Validate the shop domain
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain")
        
    # 2. Verify HMAC
    # We must rebuild the query string exactly as Shopify sent it (excluding the 'hmac' parameter itself)
    query_params = dict(request.query_params)
    query_params.pop("hmac", None)
    
    # Sort the parameters alphabetically and join with '&'
    sorted_params = "&".join([f"{k}={v}" for k, v in sorted(query_params.items())])
    
    # Calculate the HMAC SHA256 signature using the API secret
    calculated_hmac = __import__('hmac').new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        sorted_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not __import__('hmac').compare_digest(calculated_hmac, hmac):
        raise HTTPException(status_code=400, detail="HMAC validation failed - Signature does not match")

    # 3. Verify CSRF Nonce (State)
    result = await db.execute(select(StoreSettings).where(StoreSettings.shop == shop))
    store = result.scalar_one_or_none()
    
    if not store or store.nonce != state:
        raise HTTPException(status_code=400, detail="CSRF token mismatch - State parameter is invalid")

    # 4. Exchange the 'code' for a permanent 'access_token'
    async with httpx.AsyncClient() as client:
        token_url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "client_id": SHOPIFY_API_KEY,
            "client_secret": SHOPIFY_API_SECRET,
            "code": code
        }
        
        response = await client.post(token_url, json=payload)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve access token: {response.text}")
            
        data = response.json()
        access_token = data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=500, detail="Access token missing in Shopify response")
            
        # 5. Save the offline access_token in the database and clear the nonce
        store.access_token = access_token
        store.nonce = None
        
        # Mark as active since they installed
        store.is_active = True
        store.uninstalled_at = None
        await db.commit()
        
    # 6. Redirect to the Billing flow now that we have the real access_token!
    # By sending them to /api/v1/billing/subscribe, it will invoke the real Shopify GraphQL with the real token.
    return RedirectResponse(url=f"/api/v1/billing/subscribe?shop={shop}")
