from google import genai
import os
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام الإعدادات التي تتوافق مع نسخة 1.66.0
            self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # الاستدعاء المباشر المستقر
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=["Analyze this product image and give me 5 comma-separated keywords:", image_url]
            )
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Engine Error: {e}")
            return "gadget, trendy, store"
