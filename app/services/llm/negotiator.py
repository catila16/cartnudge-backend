from openai import AsyncOpenAI

client = AsyncOpenAI()

async def generate_negotiation_reply(history: list, cart_data: dict, store_limits: dict) -> str:
    """
    Uses gpt-4o for complex negotiations.
    """
    system_prompt = f"""You are 'CartNudge', an elite sales closer.
    Goal: Close the sale for the abandoned cart.
    Cart details: {cart_data}
    
    CRITICAL NEGOTIATION RULES:
    - Match the user's language and tone exactly.
    - NO PROFANITY.
    - Absolute Maximum Discount Allowed: {store_limits.get('maxDiscountMargin', 15)}%. Never exceed this under any circumstances.
    - Allow Free Shipping: {store_limits.get('allowFreeShipping', False)}. (If true, you may offer free shipping as a leverage if the user hesitates).
    - Protect merchant margins at all costs.
    - Do not offer the max discount immediately. Start small (e.g. 5%).
    - Be brief and human-like (like a WhatsApp chat).
    """
    
    messages = [{"role": "system", "content": system_prompt}] + history
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in negotiation LLM: {e}")
        return "Sanırım bir bağlantı sorunu yaşıyorum, birazdan tekrar dönüş yapacağım!"
