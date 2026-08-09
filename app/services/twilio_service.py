import os
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "whatsapp:+14155238886") # Default Twilio Sandbox Number

# Initialize client only if credentials are provided
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

def send_whatsapp_message(to_number: str, message: str) -> bool:
    """
    Sends a WhatsApp message using Twilio API.
    If credentials are not configured, it simulates the sending via logs.
    """
    # Format the number for WhatsApp if not already formatted
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    if not client:
        print("\n" + "="*50)
        print(f"📞 [MOCK TWILIO] MESSAGE SIMULATOR")
        print(f"TO: {to_number}")
        print(f"MESSAGE:\n{message}")
        print("="*50 + "\n")
        return True

    try:
        msg = client.messages.create(
            from_=TWILIO_FROM_NUMBER,
            body=message,
            to=to_number
        )
        print(f"Twilio message sent successfully! SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"Error sending Twilio message: {e}")
        return False
