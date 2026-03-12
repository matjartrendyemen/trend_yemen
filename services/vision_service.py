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
            # 1. العميل الحديث
            self.client = genai.Client(api_key=self.api_key)
            # 2. الحل هنا: كتابة اسم الموديل مباشرة بدون كلمة models/
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique keywords."
        try:
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                system_log.warning("⚠️ Using URL directly...")
                content = [prompt, image_url]
            
            # 3. الاستدعاء الصحيح الذي ينهي خطأ 404
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            # نظام الطوارئ لضمان استمرار الشيت
            system_log.error(f"❌ Vision Error Fixed Logic: {e}")
            return "gadget, trendy, store"
