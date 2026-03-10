import os
from adapters.vision_adapter import SmartVisionAdapter
from monitoring.logger import system_log

class AIService:
    def __init__(self):
        # نتحقق من وجود المفتاح أولاً
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # نستخدم الكلاس الجديد الذي أثبت نجاحه في التقرير
            self.vision_module = SmartVisionAdapter()
            self.ai_available = True
            system_log.info("✅ AI Service: SmartVisionAdapter initialized successfully.")
        else:
            system_log.warning("⚠️ GEMINI_API_KEY missing. Booting in Fallback Mode.")
            self.ai_available = False

    def get_search_keywords(self, image_url: str, fallback_text: str = "Trending products") -> str:
        if not self.ai_available:
            return fallback_text

        try:
            # نستدعي الدالة من داخل الكلاس الجديد
            return self.vision_module.extract_keywords(image_url)
        except Exception as e:
            system_log.error(f"❌ AI Service Failed: {e}. Using fallback.")
            return fallback_text

    def analyze_product_image(self, image_url):
        """دالة إضافية للتوافق مع استدعاءات الأوركستريتور"""
        return self.get_search_keywords(image_url)
