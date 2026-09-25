import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make simulation random
random_simulate = """import random

@router.post("/simulate")
async def simulate_recovery(db: AsyncSession = Depends(get_db)):
    mock_products = [
        {"title": "Shopify Reviewer Test Product", "price": "145.00"},
        {"title": "Premium Leather Jacket", "price": "299.99"},
        {"title": "Polarized Sunglasses", "price": "89.50"},
        {"title": "Smart Home Hub", "price": "120.00"},
        {"title": "Wireless Earbuds", "price": "159.00"}
    ]
    chosen = random.choice(mock_products)
    
    # Create a fake abandoned cart then resolve it
    fake_conv = Conversation(
        id=str(uuid.uuid4()),
        store_id="trycartnudge.myshopify.com",
        customer_phone="1555555" + str(uuid.uuid4().int)[:4],
        status=ConversationStatus.SUCCESS,
        conversion_type=random.choice(["AI", "AI", "AI", "HUMAN"]), # More likely AI
        cart_data={
            "total_price": chosen["price"],
            "line_items": [{"title": chosen["title"]}]
        },
        scheduled_at=datetime.utcnow()
    )
    db.add(fake_conv)
    await db.commit()
    return {"status": "ok", "message": "Simulated recovery event injected"}"""

content = re.sub(r'@router\.post\("/simulate"\).*?return \{"status": "ok", "message": "Simulated recovery event injected"\}', random_simulate, content, flags=re.DOTALL)

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated backend simulate endpoint")
