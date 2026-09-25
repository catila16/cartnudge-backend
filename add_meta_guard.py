import re

with open('app/api/v1/webhooks/whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add hmac and hashlib
if "import hmac" not in content:
    content = "import hmac\nimport hashlib\n" + content

# Function for signature verification
verify_logic = """
def verify_meta_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    signature = signature_header.split("sha256=")[1]
    expected_signature = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@router.post("/incoming")
async def receive_whatsapp_reply(
    request: Request,
    background_tasks: BackgroundTasks
):
    try:
        raw_body = await request.body()
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # Spoofing Guard: Verify X-Hub-Signature-256
    signature = request.headers.get("x-hub-signature-256")
    app_secret = os.getenv("META_APP_SECRET", "mock_secret") # Using mock for now if not set
    if app_secret:
        if not signature:
            raise HTTPException(status_code=403, detail="X-Hub-Signature-256 header missing")
        if not verify_meta_signature(raw_body, signature, app_secret):
            logger.error("Meta Webhook Signature Mismatch! Possible spoofing attack.")
            raise HTTPException(status_code=403, detail="Invalid signature")

    if body.get("object") != "whatsapp_business_account":
"""

content = re.sub(r'@router\.post\("/incoming"\)\nasync def receive_whatsapp_reply\(.*?\n    if body\.get\("object"\) != "whatsapp_business_account":', verify_logic, content, flags=re.DOTALL)

with open('app/api/v1/webhooks/whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Meta signature guard added.")
