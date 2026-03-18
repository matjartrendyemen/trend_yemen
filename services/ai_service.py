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
        هذه هي الدالة التي يستدعيها orchestrator
        ويجب أن ترجع dict متوافق مع Sheets
        """

        if not self.ai_available:
            raise Exception("AI is not available")

        try:
            # استدعاء Gemini
            result_text = self.vision_module.extract_keywords(image_url)

            # تحويل النتيجة إلى dict
            return {
                "ProductName": result_text,
                "FinalImageURL": image_url
            }

        except Exception as e:
            system_log.error(f"AI processing failed: {e}")
            raise
