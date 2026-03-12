from google import genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class VisionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام المكتبة الحديثة المستقرة
            self.client = genai.Client(api_key=self.api_key)
            # السر هنا: اسم الموديل "فقط" بدون أي مسارات
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique and specific search keywords separated by commas."
        try:
            try:
                response_img = requests.get(image_url, timeout=15)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except Exception as e:
                system_log.warning(f"⚠️ Falling back to direct URL: {e}")
                content = [prompt, image_url]
            
            # الاستدعاء المباشر الذي ينهي أسطورة الـ 404
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            
            system_log.info("✅ Vision Analysis Success: Keywords generated.")
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Final Error (Row skipped): {e}")
            return "gadget, trendy, store"
