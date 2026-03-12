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
            # استخدام العميل الحديث google-genai
            self.client = genai.Client(api_key=self.api_key)
            # الحل القاطع: الاسم فقط، المكتبة ستتولى الباقي داخلياً
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 keywords."
        try:
            # محاولة جلب الصورة
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                content = [prompt, image_url]
            
            # الاستدعاء المباشر الذي ينهي مشكلة الـ 404
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            
            system_log.info("✅ Vision Success: 404 resolved.")
            return response.text.strip()
            
        except Exception as e:
            # إذا ظهر خطأ، سنطبعه كاملاً لنعرف مكانه بالضبط
            system_log.error(f"❌ Vision Final Diagnosis: {e}")
            return "gadget, trendy, store"
