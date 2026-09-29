import httpx
import hmac
import hashlib
import json

BASE_URL = "http://localhost:8000/api/v1/webhooks/whatsapp/incoming"
APP_SECRET = "mock_secret"

def create_signature(payload: bytes, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_missing_signature():
    print("[TEST 1] Missing Signature Header")
    payload = {"object": "whatsapp_business_account"}
    response = httpx.post(BASE_URL, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 403
    print("-> PASSED (403 Forbidden)\n")

def test_invalid_signature():
    print("[TEST 2] Invalid (Spoofed) Signature Header")
    payload_dict = {"object": "whatsapp_business_account"}
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    
    headers = {
        "x-hub-signature-256": "sha256=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    }
    
    response = httpx.post(BASE_URL, content=payload_bytes, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 403
    print("-> PASSED (403 Forbidden)\n")

def test_valid_signature():
    print("[TEST 3] Valid Signature Header")
    payload_dict = {"object": "whatsapp_business_account"}
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    
    valid_sig = create_signature(payload_bytes, APP_SECRET)
    headers = {
        "x-hub-signature-256": valid_sig
    }
    
    response = httpx.post(BASE_URL, content=payload_bytes, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200
    print("-> PASSED (200 OK)\n")

if __name__ == "__main__":
    print("=== POSTMAN SECURITY GATE 2: META WEBHOOK SPOOFING TEST ===\n")
    test_missing_signature()
    test_invalid_signature()
    test_valid_signature()
    print("=== ALL SECURITY TESTS PASSED ===")
