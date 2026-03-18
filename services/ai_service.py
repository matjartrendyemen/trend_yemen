import os
from adapters.vision_adapter import SmartVisionAdapter
from monitoring.logger import system_log


class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if self.api_key:
            self.vision_module = SmartVisionAdapter()
            self.ai_available = True
            system_log.info("✅ AI Service Initialized Successfully.")
        else:
            self.ai_available = False

    def process_image(self, image_url: str) -> dict:
        """
        هذه الدالة يستدعيها orchestrator
        ويجب أن ترجع dict متوافق مع Sheets
        """

        if not self.ai_available:
            raise Exception("AI is not available")

        try:
            # استدعاء Gemini لتحليل الصورة
            result_text = self.vision_module.extract_keywords(image_url)

            # fallback لو النص فاضي
            if not result_text or not str(result_text).strip():
                result_text = "Unknown Product"

            # توليد بيانات منظمة
            return {
                "ProductName": str(result_text).strip(),
                "SKU": f"SKU-{abs(hash(image_url)) % 100000}",
                "CategoryID": "general",
                "FinalImageURL": image_url
            }

        except Exception as e:
            system_log.error(f"AI processing failed: {e}")
            raise
