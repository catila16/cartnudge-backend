import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'\'suggested_action\':.*', "'suggested_action': 'Add a 10% limited-time discount to your voice recovery flow and cross-sell Leather Care Cream (25% conversion rate).',", content)

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('../cartnudge-frontend/src/components/Phase2Dashboard.tsx', 'r', encoding='utf-8') as f:
    front = f.read()

front = front.replace('+1 Carts / $1,500.00', '{ai_insight.projected_recovery_lift}')
front = front.replace('Recovery Rate: {kpis.recovery_rate}</div>', 'Recovery Rate: {kpis.recovery_rate}%</div>')
front = front.replace('%100', '100%')
# Ensure "25%" is written instead of %25
# Wait, %25 is in frontend? No, the backend sends 25% directly. Let's make sure backend does 25%.
with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    backend = f.read()
backend = backend.replace('"25%"', '"25%"') # It's already 25% in backend.
with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(backend)

with open('../cartnudge-frontend/src/components/Phase2Dashboard.tsx', 'w', encoding='utf-8') as f:
    f.write(front)

print("Bugs fixed.")
