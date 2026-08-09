import os
from openai import AsyncOpenAI

# openai client requires OPENAI_API_KEY env var
api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-local-testing")
client = AsyncOpenAI(api_key=api_key)

async def classify_intent(message: str) -> str:
    """
    Uses gpt-4o-mini to quickly classify the user's intent.
    Returns: 'ROUTINE', 'NEGOTIATION', or 'HUMAN_REQUEST'
    """
    prompt = f"""Classify the following customer message into one of three categories:
    1. ROUTINE: Simple questions (e.g. shipping time, size guide) or generic answers.
    2. NEGOTIATION: Customer is asking for a discount, complaining about price, or negotiating.
    3. HUMAN_REQUEST: Customer explicitly asks to speak to a human or is extremely angry.
    
    Customer Message: "{message}"
    
    Respond with ONLY one word: ROUTINE, NEGOTIATION, or HUMAN_REQUEST."""
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    result = response.choices[0].message.content.strip().upper()
    if result not in ["ROUTINE", "NEGOTIATION", "HUMAN_REQUEST"]:
        return "ROUTINE"
    return result
