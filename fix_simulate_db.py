import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('customer_phone="1555555" + str(uuid.uuid4().int)[:4],', 
                          'store_id="trycartnudge.myshopify.com",\n        customer_phone="1555555" + str(uuid.uuid4().int)[:4],')

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added store_id to simulated conversation")
