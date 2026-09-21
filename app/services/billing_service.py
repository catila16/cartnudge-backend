import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Shopify API Version to use for GraphQL
SHOPIFY_API_VERSION = "2024-04"

class BillingService:
    def __init__(self, shop: str, access_token: str):
        self.shop = shop
        self.access_token = access_token
        if not self.access_token:
            raise ValueError(f"An access_token is required to initialize BillingService for {shop}")
        
        self.graphql_url = f"https://{self.shop}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

    async def _execute_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes a GraphQL query against the Shopify Admin API.
        """

        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(self.graphql_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def create_app_subscription(self, return_url: str) -> Optional[str]:
        """
        Creates a Usage-based App Subscription for 7-day free trial.
        Returns the confirmationUrl where the merchant needs to be redirected to approve the charge.
        """
        query = """
        mutation AppSubscriptionCreate($name: String!, $lineItems: [AppSubscriptionLineItemInput!]!, $returnUrl: URL!, $trialDays: Int, $test: Boolean) {
          appSubscriptionCreate(name: $name, returnUrl: $returnUrl, lineItems: $lineItems, trialDays: $trialDays, test: $test) {
            userErrors {
              field
              message
            }
            confirmationUrl
            appSubscription {
              id
            }
          }
        }
        """
        
        # We set a Capped Amount of $1000 for the usage charge
        variables = {
            "name": "CartNudge AI Recovery (Commission Based)",
            "returnUrl": return_url,
            "trialDays": 7,
            "test": True,
            "lineItems": [
                {
                    "plan": {
                        "appUsagePricingDetails": {
                            "terms": "12% for AI recovered carts, 4% for Human taken-over carts.",
                            "cappedAmount": {
                                "amount": 1000.0,
                                "currencyCode": "USD"
                            }
                        }
                    }
                }
            ]
        }

        result = await self._execute_graphql(query, variables)
        data = result.get("data", {}).get("appSubscriptionCreate", {})
        
        if data.get("userErrors"):
            logger.error(f"Error creating subscription: {data.get('userErrors')}")
            return None
            
        return data.get("confirmationUrl")

    async def create_usage_charge(self, subscription_id: str, amount: float, description: str) -> bool:
        """
        Creates an App Usage Record (a charge) against the merchant's active usage subscription.
        """
        query = """
        mutation appUsageRecordCreate($subscriptionLineItemId: ID!, $price: MoneyInput!, $description: String!) {
          appUsageRecordCreate(subscriptionLineItemId: $subscriptionLineItemId, price: $price, description: $description) {
            userErrors {
              field
              message
            }
            appUsageRecord {
              id
            }
          }
        }
        """
        
        variables = {
            "subscriptionLineItemId": subscription_id,
            "price": {
                "amount": round(amount, 2),
                "currencyCode": "USD" # Ideally this matches the store's currency
            },
            "description": description
        }

        result = await self._execute_graphql(query, variables)
        data = result.get("data", {}).get("appUsageRecordCreate", {})
        
        if data.get("userErrors"):
            logger.error(f"Error creating usage charge: {data.get('userErrors')}")
            return False
            
        return True
