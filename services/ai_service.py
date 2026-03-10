import os
import google.genai as genai
from monitoring.logger import system_log
from adapters.vision_adapter import extract_keywords_from_image

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            # نحفظ اسم الموديل فقط
            self.model = "models/gemini-2.5-flash"
            self.ai_available = True
        else:
            system_log.warning("GEMINI_API_KEY missing. Booting in NON-AI Fallback Mode.")
            self.ai_available = False

    def get_search_keywords(self, image_url: str, fallback_text: str = "Trending products") -> str:
        if not self.ai_available:
            system_log.info(f"AI offline. Using fallback text: {fallback_text}")
            return fallback_text

        try:
            system_log.info("AI online. Passing model to Vision Adapter...")
            # نمرر self.model وليس كائن الاستجابة
            return extract_keywords_from_image(self.model, image_url)
        except Exception as e:
            system_log.error(f"AI Vision Failed: {e}. Using fallback text.")
            return fallback_text
