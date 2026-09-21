import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api.v1.webhooks import shopify, whatsapp, gdpr
from app.api.v1 import live_support
from app.core.database import engine, Base

app = FastAPI(title="CartNudge Backend", version="1.0.0")

@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "frame-ancestors https://*.myshopify.com https://admin.shopify.com;"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3005", "https://trycartnudge.com", "https://www.trycartnudge.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Routes
app.include_router(shopify.router, prefix="/api/v1/webhooks/shopify", tags=["Shopify Webhooks"])
app.include_router(whatsapp.router, prefix="/api/v1/webhooks/whatsapp", tags=["WhatsApp Webhooks"])
app.include_router(gdpr.router, prefix="/api/v1/webhooks/gdpr", tags=["GDPR Webhooks"])
app.include_router(live_support.router, prefix="/api/v1/live-support", tags=["Live Support"])

from app.api.v1 import dashboard, admin, billing, auth
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["OAuth"])

@app.on_event("startup")
async def on_startup():
    from app.core.database import DATABASE_URL
    import urllib.parse
    
    parsed = urllib.parse.urlparse(DATABASE_URL)
    safe_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
    print(f"Starting up CartNudge Backend... Connecting to {safe_url}")
    
    # Initialize DB tables for testing (in production use Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Quick migration for new columns
        from sqlalchemy import text
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "access_token" VARCHAR'))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "nonce" VARCHAR'))
        except Exception: pass
        
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "aiPersonaTone" VARCHAR DEFAULT \'Friendly & Convincing\''))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "country_code" VARCHAR(5) DEFAULT \'US\''))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "is_active" BOOLEAN DEFAULT 1'))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "uninstalled_at" DATETIME'))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "billing_charge_id" VARCHAR'))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "billing_status" VARCHAR DEFAULT \'PENDING\''))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "StoreSettings" ADD COLUMN "trial_ends_at" DATETIME'))
        except Exception: pass
            
        try:
            await conn.execute(text('ALTER TABLE "conversations" ADD COLUMN "last_customer_message_at" DATETIME'))
        except Exception: pass
        
        try:
            await conn.execute(text('ALTER TABLE "conversations" ADD COLUMN "chat_history" JSON DEFAULT \'[]\''))
        except Exception: pass

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
        
    file_path = os.path.join("static", full_path)
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
