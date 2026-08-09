from fastapi import FastAPI
from app.api.v1.webhooks import shopify, whatsapp, gdpr
from app.api.v1 import live_support
from app.core.database import engine, Base

app = FastAPI(title="CartNudge Backend", version="1.0.0")

# Setup Routes
app.include_router(shopify.router, prefix="/api/v1/webhooks/shopify", tags=["Shopify Webhooks"])
app.include_router(whatsapp.router, prefix="/api/v1/webhooks/whatsapp", tags=["WhatsApp Webhooks"])
app.include_router(gdpr.router, prefix="/api/v1/webhooks/gdpr", tags=["GDPR Webhooks"])
app.include_router(live_support.router, prefix="/api/v1/live-support", tags=["Live Support"])

@app.on_event("startup")
async def on_startup():
    print("Starting up CartNudge Backend...")
    # Initialize DB tables for testing (in production use Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {"status": "CartNudge Engine is running."}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
