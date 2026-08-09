import uuid

def generate_discount_url(conversation_id: str, discount_percentage: int, store_id: str) -> str:
    """
    Simulates calling Shopify GraphQL API (e.g. discountCodeBasicCreate) 
    to create a single-use dynamic discount code.
    """
    
    # In production, we would use Shopify GraphQL API with the store's access token
    # to create a discount code restricted to the specific items or the specific customer.
    
    # Generate a unique, short, hard-to-guess dynamic coupon code
    short_uuid = str(uuid.uuid4())[:8].upper()
    coupon_code = f"CN-{discount_percentage}-{short_uuid}"
    
    print(f"[SHOPIFY API] Created dynamic {discount_percentage}% discount code: {coupon_code} for store {store_id}")
    
    # We use a simulated checkout token extracted from the conversation_id
    checkout_token = conversation_id.replace("conv_", "")
    
    # Auto-applied checkout URL format
    checkout_url = f"https://{store_id}/cart/c/{checkout_token}?discount={coupon_code}"
    
    return checkout_url
