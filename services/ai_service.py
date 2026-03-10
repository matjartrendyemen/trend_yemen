import os
import google.generativeai as genai
from monitoring.logger import system_log
from adapters.vision_adapter import extract_keywords_from_image

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINIAPIKEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('models/gemini-2.5-flash')
            self.ai_available = True
        else:
            system_log.warning("GEMINIAPIKEY missing. Booting in NON-AI Fallback Mode.")
            self.ai_available = False

    def get_search_keywords(self, image_url: str, fallback_text: str = "Trending products") -> str:
        if not self.ai_available:
            system_log.info(f"AI offline. Using fallback text: {fallback_text}")
            return fallback_text

        try:
            system_log.info("AI online. Analyzing image...")
            keywords = extract_keywords_from_image(self.model, image_url)
            return keywords
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "exhausted" in error_msg:
                system_log.critical("AI QUOTA EXHAUSTED! Switching to Fallback Mode permanently.")
                self.ai_available = False
                return fallback_text
            system_log.error(f"AI Vision Failed: {e}. Using fallback text.")
            return fallback_text
