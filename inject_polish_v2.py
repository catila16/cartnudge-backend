import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Price Resistance Detected', 'Break Price Resistance via Voice Discounts')
content = content.replace('Most of the lost sales are due to price objections.', 'High Price Resistance')
content = content.replace("Increase the max discount ceiling to 18% to recover 1 more cart.", "Add a 10% limited-time discount to your voice recovery flow and cross-sell Leather Care Cream (25% conversion rate).")
content = content.replace('+1 Carts / $1,500.00', '+1 Cart / $1,500.00')
content = content.replace('"rate": "%25"', '"rate": "25%"')
content = content.replace("'rate': '%25'", "'rate': '25%'")

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backend polished v2.")
