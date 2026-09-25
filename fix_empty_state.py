import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_logic = """
        if total_abandoned == 0:
            ai_insight = {
                'headline': 'CartNudge is listening for cart events.',
                'primary_bottleneck': 'Awaiting Data',
                'suggested_action': 'Your AI insights will appear here once abandoned carts are tracked.',
                'projected_recovery_lift': 'Waiting...',
                'urgency_level': 'LOW'
            }
            return {
                "success": True,
                "kpis": {
                    "total_abandoned": 0,
                    "recovery_rate": 0.0,
                    "recovered_revenue": 0.0,
                    "cross_sell_revenue": 0.0,
                    "voice_recovered_count": 0
                },
                "lost_sales": [{"name": "WAITING_FOR_DATA", "value": 1}],
                "cross_sell": [],
                "ai_insight": ai_insight
            }
            
        try:
"""
content = content.replace("        try:\n            ai_insight_model = await advisor_agent.generate_merchant_insight(", new_logic + "            ai_insight_model = await advisor_agent.generate_merchant_insight(")

# In the dashboard frontend, if lost_sales has WAITING_FOR_DATA, maybe display "Waiting for first abandoned cart"
# We can do that by setting the name to "Waiting for data".

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Empty state fallback injected.")
