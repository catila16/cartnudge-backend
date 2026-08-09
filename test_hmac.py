import os
import hmac
import hashlib
import base64
import asyncio
from fastapi import Request, HTTPException
from app.core.security import verify_shopify_hmac, SHOPIFY_API_SECRET

# Mock a raw payload
payload = b'{"customer":{"id":12345,"phone":"+905550001122"}}'

# Compute valid HMAC
computed_hmac = hmac.new(
    SHOPIFY_API_SECRET.encode('utf-8'),
    payload,
    hashlib.sha256
).digest()
valid_hmac_header = base64.b64encode(computed_hmac).decode('utf-8')

class MockRequest:
    def __init__(self, headers, body_bytes):
        self.headers = headers
        self._body = body_bytes
        self.state = type('State', (), {})()
        
    async def body(self):
        return self._body

async def test_hmac():
    print("--- Testing Valid HMAC ---")
    valid_req = MockRequest(headers={"X-Shopify-Hmac-Sha256": valid_hmac_header}, body_bytes=payload)
    try:
        await verify_shopify_hmac(valid_req)
        print("Success! HMAC validated and raw_body saved to state.")
    except Exception as e:
        print("Failed:", e)

    print("\n--- Testing Invalid HMAC ---")
    invalid_req = MockRequest(headers={"X-Shopify-Hmac-Sha256": "invalid_hash_string="}, body_bytes=payload)
    try:
        await verify_shopify_hmac(invalid_req)
        print("Failed: Should have raised exception.")
    except HTTPException as e:
        print("Success! Caught invalid HMAC with status:", e.status_code)

if __name__ == "__main__":
    asyncio.run(test_hmac())
