import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('"rate": "25.0%"', '"rate": "%25"')
content = content.replace("₺1.500'", "₺1.500,00'")

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backend polished.")
