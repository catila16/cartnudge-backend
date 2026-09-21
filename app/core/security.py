import os
import hmac
import hashlib
import base64
import logging
from fastapi import Request, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# The secret key for Shopify HMAC verification. 
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "dummy_secret")

async def verify_shopify_hmac(request: Request, x_shopify_hmac_sha256: str = Header(None)):
    """
    Shopify'dan gelen X-Shopify-Hmac-Sha256 başlığını ve ham gövdeyi (raw body) doğrular.
    """
    if not x_shopify_hmac_sha256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Eksik Shopify HMAC başlığı"
        )

    # Webhook gövdesini ham byte dizisi olarak oku
    body_bytes = await request.body()
    
    # HMAC SHA256 hesapla
    digest = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).digest()
    
    calculated_hmac = base64.b64encode(digest).decode("utf-8")

    print(f"SECRET: {SHOPIFY_API_SECRET[:5]}...{SHOPIFY_API_SECRET[-5:]}")
    print(f"CALCULATED: {calculated_hmac}")
    print(f"RECEIVED: {x_shopify_hmac_sha256}")

    # Zamanlama saldırılarına (timing attack) karşı güvenli karşılaştırma
    if not hmac.compare_digest(calculated_hmac, x_shopify_hmac_sha256):
        logger.error(f"HMAC mismatch! Invalid Shopify webhook signature.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz Shopify webhook imzası"
        )

    return body_bytes

# --- Admin Panel JWT Security ---

ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "super-secret-cartnudge-admin-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

admin_security = HTTPBearer()

def create_admin_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "role": "super_admin", "exp": expire}
    return jwt.encode(to_encode, ADMIN_JWT_SECRET, algorithm=ALGORITHM)

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role != "super_admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yetkisiz erişim")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz veya süresi dolmuş token")
