import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update CSP middleware
new_middleware = """@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "frame-ancestors https://admin.shopify.com https://*.myshopify.com;"
    
    # Pre-Flight: Remove X-Frame-Options to avoid conflicting with CSP in embedded mode
    if "X-Frame-Options" in response.headers:
        del response.headers["X-Frame-Options"]
    if "x-frame-options" in response.headers:
        del response.headers["x-frame-options"]
        
    return response"""

content = re.sub(r'@app\.middleware\("http"\).*?return response', new_middleware, content, flags=re.DOTALL)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("CSP middleware updated.")
