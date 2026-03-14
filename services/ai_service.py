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

    def analyze_product_image(self, image_url: str) -> str:
        if not self.ai_available: return "AI_OFFLINE"
        return self.vision_module.extract_keywords(image_url)
