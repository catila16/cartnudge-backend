import io
import re
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

FALLBACK_MESSAGES = {
    "en": {
        "audio_error": "We couldn't load your voice note. Could you please send it again or type your message?",
        "not_understood": "Sorry, I couldn't quite catch that. Could you please repeat or type it out?"
    },
    "de": {
        "audio_error": "Wir konnten Ihre Sprachnachricht nicht laden. Bitte senden Sie sie erneut oder schreiben Sie uns.",
        "not_understood": "Entschuldigung, das habe ich leider nicht verstanden. Könnten Sie es bitte wiederholen oder schreiben?"
    },
    "tr": {
        "audio_error": "Ses kaydınız alınamadı. Lütfen tekrar gönderin veya mesaj olarak yazın.",
        "not_understood": "Sesinizi tam anlayamadım. Tekrar ses gönderebilir veya mesaj olarak yazabilirsiniz."
    },
    "fr": {
        "audio_error": "Impossible de charger votre message vocal. Pourriez-vous le renvoyer ou l'écrire ?",
        "not_understood": "Désolé, je n'ai pas bien compris. Pourriez-vous répéter ou l'écrire ?"
    },
    "es": {
        "audio_error": "No pudimos cargar su nota de voz. ¿Podría enviarla de nuevo o escribirla?",
        "not_understood": "Lo siento, no pude entenderlo. ¿Podría repetirlo o escribirlo?"
    }
}

class AntigravityVoiceResolver:
    def __init__(self, openai_api_key: str):
        self.whisper_client = AsyncOpenAI(api_key=openai_api_key)

    @staticmethod
    def get_fallback_text(locale: Optional[str], key: str) -> str:
        lang = (re.split(r"[-_]", locale.strip().lower())[0] if locale else "en")
        dict_lang = FALLBACK_MESSAGES.get(lang, FALLBACK_MESSAGES["en"])
        return dict_lang.get(key, FALLBACK_MESSAGES["en"][key])

    async def transcribe_voice(
        self,
        audio_bytes: bytes,
        customer_locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bellek içindeki (RAM) ses baytlarını Whisper'a aktarır.
        Shopify locale varsa dil zorlamasıyla (~700ms), expat/belirsiz senaryoda oto-tespitle çalışır.
        """
        # Meta sends audio/ogg
        audio_file = ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg")
        
        target_lang = None
        if customer_locale:
            clean_lang = re.split(r"[-_]", customer_locale.strip().lower())[0]
            if clean_lang in FALLBACK_MESSAGES:
                target_lang = clean_lang

        payload: Dict[str, Any] = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "verbose_json"
        }
        if target_lang:
            payload["language"] = target_lang

        try:
            resp = await self.whisper_client.audio.transcriptions.create(**payload)
            # handle sync vs async properly depending on OpenAI client, AsyncOpenAI uses await
            return {
                "success": True,
                "text": resp.text.strip(),
                "detected_language": getattr(resp, "language", target_lang or "auto")
            }
        except Exception as e:
            logger.error(f"Whisper Transcription error: {e}")
            return {"success": False, "error": str(e), "text": ""}
