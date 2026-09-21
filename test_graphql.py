import asyncio
import httpx
import sqlite3

async def main():
    conn = sqlite3.connect('cartnudge.db')
    try:
        token = conn.execute("SELECT access_token FROM StoreSettings WHERE shop='cartnudge-xr23a9yy.myshopify.com'").fetchone()[0]
        print(f"Token: {token}")
    except Exception as e:
        print("Failed to get token:", e)
        return
        
    query = """
    mutation AppSubscriptionCreate($name: String!, $lineItems: [AppSubscriptionLineItemInput!]!, $returnUrl: URL!, $test: Boolean) {
      appSubscriptionCreate(name: $name, returnUrl: $returnUrl, lineItems: $lineItems, test: $test) {
        userErrors { message }
      }
    }
    """
    variables = {
        "name": "Test",
        "returnUrl": "https://google.com",
        "test": True,
        "lineItems": [{"plan": {"appUsagePricingDetails": {"terms": "1", "cappedAmount": {"amount": 10, "currencyCode": "USD"}}}}]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://cartnudge-xr23a9yy.myshopify.com/admin/api/2024-04/graphql.json',
            headers={'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'},
            json={'query': query, 'variables': variables}
        )
        print("Status:", resp.status_code)
        print("Response:", resp.text)

if __name__ == "__main__":
    asyncio.run(main())
