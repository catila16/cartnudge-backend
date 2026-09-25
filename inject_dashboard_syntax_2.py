import re

with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'suggested_action': 'Maksimum indirim tavanını %18'e çıkararak 1 sepeti daha kurtarabilirsiniz.',",
                          "'suggested_action': \"Maksimum indirim tavanını %18'e çıkararak 1 sepeti daha kurtarabilirsiniz.\",")

with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
