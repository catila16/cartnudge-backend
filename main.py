from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Routes
app.include_router(shopify.router, prefix="/api/v1/webhooks/shopify", tags=["Shopify Webhooks"])
app.include_router(whatsapp.router, prefix="/api/v1/webhooks/whatsapp", tags=["WhatsApp Webhooks"])
app.include_router(gdpr.router, prefix="/api/v1/webhooks/gdpr", tags=["GDPR Webhooks"])
app.include_router(live_support.router, prefix="/api/v1/live-support", tags=["Live Support"])

from app.api.v1 import dashboard
app.include_router(dashboard.router)

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
