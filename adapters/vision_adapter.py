from google import genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # الحل الجديد: تحديد الإصدار v1beta بشكل صريح في الإعدادات
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={'api_version': 'v1beta'}
            )
            # نستخدم الاسم المجرد تماماً
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image and provide 5 search keywords."
        try:
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                content = [prompt, image_url]
            
            # الطلب المباشر
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            return response.text.strip()
        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {e}")
            return "gadget, trendy, store"
