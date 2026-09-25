import re

# 1. Update backend to add /simulate endpoint
with open('app/api/v1/routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

simulate_endpoint = """
from app.models.conversation import ConversationStatus
import uuid
from datetime import datetime

@router.post("/simulate")
async def simulate_recovery(db: AsyncSession = Depends(get_db)):
    # Create a fake abandoned cart then resolve it
    fake_conv = Conversation(
        id=str(uuid.uuid4()),
        customer_phone="1555555" + str(uuid.uuid4().int)[:4],
        status=ConversationStatus.SUCCESS,
        cart_data={
            "total_price": "145.00",
            "line_items": [{"title": "Shopify Reviewer Test Product"}]
        },
        scheduled_at=datetime.utcnow()
    )
    db.add(fake_conv)
    await db.commit()
    return {"status": "ok", "message": "Simulated recovery event injected"}
"""

content = content + simulate_endpoint
with open('app/api/v1/routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update frontend client.ts
with open('src/api/client.ts', 'r', encoding='utf-8') as f:
    client_content = f.read()

client_content += """
export const simulateRecovery = async (): Promise<any> => {
  const response = await apiClient.post('/api/dashboard/simulate');
  return response.data;
};
"""
with open('src/api/client.ts', 'w', encoding='utf-8') as f:
    f.write(client_content)

# 3. Update LiveCartsTable.tsx
with open('src/components/LiveCartsTable.tsx', 'r', encoding='utf-8') as f:
    table_content = f.read()

table_content = table_content.replace(
    "import { getActiveConversations, triggerTakeover } from '../api/client';",
    "import { getActiveConversations, triggerTakeover, simulateRecovery } from '../api/client';\nimport { Play } from 'lucide-react';"
)
table_content = table_content.replace(
    "import { Clock, User, CheckCircle, Hand, MessageCircle, AlertCircle } from 'lucide-react';",
    "import { Clock, User, CheckCircle, Hand, MessageCircle, AlertCircle, Play } from 'lucide-react';"
)

simulate_func = """
  const handleSimulate = async () => {
    try {
      await simulateRecovery();
      // Fetch immediately
      const data = await getActiveConversations();
      setCarts(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTakeover = async (id: string) => {"""

table_content = table_content.replace("  const handleTakeover = async (id: string) => {", simulate_func)

old_header = """        <span className="flex items-center gap-2 text-sm text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
          </span>
          Live Monitoring
        </span>"""
# Wait, I didn't replace it in apply_design_system.py, I used cyber -> emerald-400! Let's check what it is right now.
