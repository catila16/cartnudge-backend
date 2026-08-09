import requests
import time

url = "http://127.0.0.1:8000/api/v1/webhooks/shopify/checkouts/update"

def send_test(name, payload):
    print(f"\n--- Testing: {name} ---")
    try:
        response = requests.post(url, json=payload, timeout=2)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

base_settings = {
    "maxDiscountMargin": 15,
    "cartAbandonmentDelay": 50,
    "cartFollowupHours": 12,
    "minCartAmount": 40,
    "quietHoursEnabled": True,
    "quietHoursStart": "23:00",
    "quietHoursEnd": "09:00",
    "allowFreeShipping": True
}

# Test 1: Below Min Cart
send_test("Below Min Cart Amount ($30)", {
    "checkout": {
        "token": "token_below_min_cart",
        "total_price": "30.00"
    },
    "store_settings": base_settings
})

time.sleep(1)

# Test 2: Above Min Cart
send_test("Valid Cart Amount ($50)", {
    "checkout": {
        "token": "token_valid_cart",
        "total_price": "50.00"
    },
    "store_settings": base_settings
})

time.sleep(1)

# Test 3: Idempotency (Duplicate token)
send_test("Duplicate Token", {
    "checkout": {
        "token": "token_valid_cart",
        "total_price": "50.00"
    },
    "store_settings": base_settings
})
