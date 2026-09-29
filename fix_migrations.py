import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_migrations = """
        # Quick migration for new columns
        from sqlalchemy import text
        is_pg = "postgres" in DATABASE_URL
        timestamp_type = "TIMESTAMP" if is_pg else "DATETIME"
        true_val = "true" if is_pg else "1"
        
        migrations = [
            'ALTER TABLE "StoreSettings" ADD COLUMN "access_token" VARCHAR',
            'ALTER TABLE "StoreSettings" ADD COLUMN "nonce" VARCHAR',
            'ALTER TABLE "StoreSettings" ADD COLUMN "aiPersonaTone" VARCHAR DEFAULT \\'Friendly & Convincing\\'',
            'ALTER TABLE "StoreSettings" ADD COLUMN "country_code" VARCHAR(5) DEFAULT \\'US\\'',
            f'ALTER TABLE "StoreSettings" ADD COLUMN "is_active" BOOLEAN DEFAULT {true_val}',
            f'ALTER TABLE "StoreSettings" ADD COLUMN "uninstalled_at" {timestamp_type}',
            'ALTER TABLE "StoreSettings" ADD COLUMN "billing_charge_id" VARCHAR',
            'ALTER TABLE "StoreSettings" ADD COLUMN "billing_status" VARCHAR DEFAULT \\'PENDING\\'',
            f'ALTER TABLE "StoreSettings" ADD COLUMN "trial_ends_at" {timestamp_type}',
            f'ALTER TABLE "conversations" ADD COLUMN "last_customer_message_at" {timestamp_type}',
            'ALTER TABLE "conversations" ADD COLUMN "chat_history" JSON DEFAULT \\'[]\\'',
            'ALTER TABLE "conversations" ADD COLUMN "conversion_type" VARCHAR',
            'ALTER TABLE "conversations" ADD COLUMN "applied_commission_rate" NUMERIC(4, 2)',
            'ALTER TABLE "conversations" ADD COLUMN "total_recovered_amount" NUMERIC(10, 2) DEFAULT 0.00',
            'ALTER TABLE "conversations" ADD COLUMN "commission_earned" NUMERIC(10, 2) DEFAULT 0.00',
            'ALTER TABLE "conversations" ADD COLUMN "offered_cross_sell_variant_id" VARCHAR',
            'ALTER TABLE "conversations" ADD COLUMN "lost_sale_category" VARCHAR',
            'ALTER TABLE "conversations" ADD COLUMN "lost_sale_detail" VARCHAR',
            f'ALTER TABLE "conversations" ADD COLUMN "last_human_activity_at" {timestamp_type}',
        ]
        
        for q in migrations:
            try:
                await conn.execute(text(q))
            except Exception as e:
                pass
"""

pattern = re.compile(r'# Quick migration for new columns.*?(?=@app\.get)', re.DOTALL)
new_content = pattern.sub(new_migrations + "\n", content)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Migration fix applied.")
