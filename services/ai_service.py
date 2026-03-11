import os
from adapters.vision_adapter import SmartVisionAdapter
from monitoring.logger import system_log

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                self.vision_module = SmartVisionAdapter()
                self.ai_available = True
                system_log.info("✅ AI Service: SmartVisionAdapter ready.")
            except Exception as e:
                system_log.error(f"❌ VisionAdapter Init Error: {e}")
                self.ai_available = False
        else:
            system_log.warning("⚠️ GEMINI_API_KEY missing. AI disabled.")
            self.ai_available = False

    def analyze_product_image(self, image_url: str) -> str:
        """الدالة الأساسية التي يستدعيها الأوركستريتور"""
        if not self.ai_available:
            return "AI_UNAVAILABLE"

        try:
            # استخراج الكلمات المفتاحية
            keywords = self.vision_module.extract_keywords(image_url)
            return keywords if keywords else "No keywords found"
        except Exception as e:
            system_log.error(f"❌ AI Analysis Failed: {e}")
            return f"Error: {str(e)}"
