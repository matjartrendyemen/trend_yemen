import os
import google.genai as genai
from monitoring.logger import system_log
from adapters.vision_adapter import extract_keywords_from_image

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # إنشاء Client باستخدام المفتاح
            self.client = genai.Client(api_key=self.api_key)
            # حفظ اسم الموديل فقط
            self.model = "models/gemini-2.5-flash"
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
            # استدعاء الموديل عبر client.models.generate_content
            response = self.client.models.generate_content(
                model=self.model,
                contents=image_url
            )
            # استخراج النص الناتج من الاستجابة
            keywords = response.text
            # تمرير النص إلى الـ adapter إذا أردت معالجة إضافية
            keywords = extract_keywords_from_image(keywords, image_url)
            return keywords
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "exhausted" in error_msg:
                system_log.critical("AI QUOTA EXHAUSTED! Switching to Fallback Mode permanently.")
                self.ai_available = False
                return fallback_text
            system_log.error(f"AI Vision Failed: {e}. Using fallback text.")
            return fallback_text
