import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Fiyat Direnci Tespit Edildi', 'Price Resistance Detected')
content = content.replace('Kayıp satışların çoğu fiyat itirazından kaynaklanıyor.', 'Most of the lost sales are due to price objections.')
content = content.replace("Maksimum indirim tavanını %18\\'e çıkararak 1 sepeti daha kurtarabilirsiniz.", "Increase the max discount ceiling to 18% to recover 1 more cart.")
content = content.replace('+1 Sepet / ₺1.500,00', '+1 Carts / $1,500.00')

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backend translated.")
