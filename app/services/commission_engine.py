from decimal import Decimal
from app.models.conversation import Conversation, ConversationStatus
from app.models.store import Store

class CommissionEngine:
    @staticmethod
    def calculate_and_apply(conversation: Conversation, store: Store, order_amount: Decimal):
        if conversation.status == ConversationStatus.HUMAN_ACTIVE or conversation.last_human_activity_at is not None:
            rate = store.assisted_commission_rate
            conversion_type = "ASSISTED"
        else:
            rate = store.bot_commission_rate
            conversion_type = "BOT"

        calculated_earned = (order_amount * rate) / Decimal("100.00")
        earned = max(calculated_earned, store.min_fee_guard)

        conversation.conversion_type = conversion_type
        conversation.applied_commission_rate = rate
        conversation.total_recovered_amount = order_amount
        conversation.commission_earned = earned
        conversation.status = ConversationStatus.SUCCESS
        
        return conversation
