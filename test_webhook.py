import hmac
import hashlib
import base64
import json
import urllib.request
import urllib.error

secret = "dummy_secret"
url = "http://localhost:8000/api/v1/webhooks/shopify/checkouts/update"

payload = {
    "token": "test-checkout-12345",
    "total_price": "45.00",
    "phone": "+905345900476",
    "customer": {
        "first_name": "Caner",
    },
    "abandoned_checkout_url": "https://test.myshopify.com/checkouts/test-12345",
    "shipping_address": {
        "country_code": "TR"
    },
    "store_settings": {
        "cartAbandonmentDelay": 1,
        "minCartAmount": 10
    }
}

body = json.dumps(payload).encode('utf-8')

digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
hmac_header = base64.b64encode(digest).decode('utf-8')

req = urllib.request.Request(url, data=body)
req.add_header('Content-Type', 'application/json')
req.add_header('X-Shopify-Hmac-Sha256', hmac_header)

print(f"Sending webhook to {url}")
print(f"HMAC Header: {hmac_header}")

try:
    with urllib.request.urlopen(req) as response:
        print("Response Code:", response.getcode())
        print("Response Body:", response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Error Body:", e.read().decode())
except Exception as e:
    print("Error:", e)
