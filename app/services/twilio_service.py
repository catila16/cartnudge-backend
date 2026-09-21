import os
import json
import phonenumbers
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class TwilioService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        # Twilio Content Template SID'leri (.env üzerinden tanımlanabilir)
        self.template_sids = {
            "tr": os.getenv("TWILIO_TEMPLATE_SID_TR", "HX_TR_TEMPLATE_SID"),
            "de": os.getenv("TWILIO_TEMPLATE_SID_DE", "HX_DE_TEMPLATE_SID"),
            "en": os.getenv("TWILIO_TEMPLATE_SID_EN", "HX_EN_TEMPLATE_SID"),
        }

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None

    def detect_language(self, phone_number: str, country_code: str = None) -> str:
        """
        Ülke kodu veya telefon numarasından dil tespiti yapar.
        """
        if country_code:
            code = country_code.upper()
            if code in ["TR"]: return "tr"
            if code in ["DE", "AT", "CH"]: return "de"

        try:
            parsed = phonenumbers.parse(phone_number, None)
            region = phonenumbers.region_code_for_number(parsed)
            if region == "TR": return "tr"
            if region in ["DE", "AT", "CH"]: return "de"
        except Exception:
            pass

        return "en"  # Varsayılan global dil

    def format_to_e164(self, phone_number: str) -> str:
        try:
            parsed = phonenumbers.parse(phone_number, None)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            return phone_number if phone_number.startswith("+") else f"+{phone_number}"

    def send_whatsapp_template(
        self, 
        to_phone: str, 
        customer_name: str, 
        checkout_url: str, 
        country_code: str = None
    ) -> dict:
        """
        Meta onaylı Twilio Content Template mesajı fırlatır.
        """
        e164_number = self.format_to_e164(to_phone)
        whatsapp_to = f"whatsapp:{e164_number}"
        lang = self.detect_language(e164_number, country_code)
        content_sid = self.template_sids.get(lang, self.template_sids["en"])

        # Şablon değişkenleri: {{1}} -> İsim, {{2}} -> Checkout Linki
        content_variables = json.dumps({
            "1": customer_name or "there",
            "2": checkout_url
        })

        if not self.client:
            print(f"[Twilio Dry-Run] Template SID: {content_sid} | To: {whatsapp_to} | Vars: {content_variables}")
            return {"status": "simulated", "content_sid": content_sid, "to": whatsapp_to}

        try:
            message = self.client.messages.create(
                from_=self.from_number,
                to=whatsapp_to,
                content_sid=content_sid,
                content_variables=content_variables
            )
            return {"status": "success", "sid": message.sid, "state": message.status}
        except TwilioRestException as e:
            print(f"[Twilio Error] {e.msg}")
            return {"status": "error", "message": e.msg}

    def send_whatsapp_message(self, to_phone: str, message: str) -> dict:
        """
        Meta kuralları gereği müşteri cevap verdikten sonra 24 saat içinde 
        serbest metin (free-form) mesaj göndermek için kullanılır.
        """
        e164_number = self.format_to_e164(to_phone)
        whatsapp_to = f"whatsapp:{e164_number}"

        if not self.client:
            print(f"[Twilio Dry-Run] Text Message | To: {whatsapp_to} | Body: {message}")
            return {"status": "simulated", "to": whatsapp_to, "body": message}

        try:
            msg = self.client.messages.create(
                from_=self.from_number,
                to=whatsapp_to,
                body=message
            )
            return {"status": "success", "sid": msg.sid, "state": msg.status}
        except TwilioRestException as e:
            print(f"[Twilio Error] {e.msg}")
            return {"status": "error", "message": e.msg}

twilio_service = TwilioService()
