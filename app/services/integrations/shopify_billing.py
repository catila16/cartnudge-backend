import logging
import requests

logger = logging.getLogger(__name__)

def charge_store_commission(store_domain: str, access_token: str, subscription_line_item_id: str, recovered_amount: float, conversion_type: str, min_fee_guard: float = 0.50):
    """
    Calls Shopify GraphQL API to create an appUsageRecord for usage-based billing.
    
    conversion_type: "BOT" (12% commission) or "ASSISTED" (4% commission)
    min_fee_guard: Minimum fee to charge if the percentage is too low.
    """
    # Determine the rate
    if conversion_type == "BOT":
        rate = 0.12
    elif conversion_type == "ASSISTED":
        rate = 0.04
    else:
        logger.error(f"Unknown conversion_type {conversion_type}. Skipping billing.")
        return False

    # Calculate fee
    calculated_fee = recovered_amount * rate
    
    # Enforce minimum fee guard
    final_fee = max(calculated_fee, min_fee_guard)
    
    # Format description
    description = f"CartNudge Recovery Commission - {conversion_type} (Recovered: ${recovered_amount:.2f})"
    
    query = """
    mutation appUsageRecordCreate($description: String!, $price: MoneyInput!, $subscriptionLineItemId: ID!) {
      appUsageRecordCreate(description: $description, price: $price, subscriptionLineItemId: $subscriptionLineItemId) {
        appUsageRecord {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "description": description,
        "price": {
            "amount": round(final_fee, 2),
            "currencyCode": "USD"
        },
        "subscriptionLineItemId": subscription_line_item_id
    }
    
    # Simulate API call to Shopify
    logger.info(f"[BILLING] Simulating charge to {store_domain} for {description}. Fee: ${final_fee:.2f}")
    
    # In production:
    # url = f"https://{store_domain}/admin/api/2023-10/graphql.json"
    # headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
    # response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    # data = response.json()
    
    # Simulating a mocked response for MVP testing
    mocked_data = {
        "data": {
            "appUsageRecordCreate": {
                "appUsageRecord": {"id": "gid://shopify/AppUsageRecord/123456"},
                "userErrors": [] # User requested to check this array
            }
        }
    }
    
    # Extract errors (Crucial requirement from the user)
    user_errors = mocked_data.get("data", {}).get("appUsageRecordCreate", {}).get("userErrors", [])
    
    if user_errors:
        for error in user_errors:
            logger.error(f"[BILLING ERROR] {store_domain} - {error.get('field')}: {error.get('message')}")
        return False
        
    logger.info(f"[BILLING SUCCESS] Successfully charged ${final_fee:.2f} to {store_domain}")
    return True
