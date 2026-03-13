import os
import requests
from io import BytesIO
from PIL import Image
from google import genai
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # الربط الصريح بـ v1beta كما في المستند rp.txt
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            # السر في المستند: استخدام اسم الموديل المجرد
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        system_log.info(f"📸 Decoding Image from: {image_url}")
        try:
            # 1. جلب الصورة (التقرير الناجح استخدم requests.get)
            # تنبيه: روابط Google Drive تحتاج أحياناً لمعالجة خاصة، لكننا سنلتزم بمنطق التقرير
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()

            # 2. معالجة الصورة وتحويلها لـ Bytes (مطابق للسطر 268 في rp.txt)
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")
            
            # 3. بناء الطلب بنفس الهيكل الذي نجح قبل 3 أيام (السطر 275)
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Analyze this product image and return 4 precise English keywords separated by commas."},
                            {"inline_data": {"mime_type": mime_type, "data": img_data}}
                        ]
                    }
                ]
            )

            if result and result.text:
                keywords = result.text.strip().replace("\n", " ")
                system_log.info(f"✅ AI Response Success: {keywords}")
                return keywords
            
            return "gadget, trendy, store"

        except Exception as e:
            # طباعة الخطأ كاملاً للتدقيق إذا فشل
            system_log.error(f"❌ Vision Execution Error: {str(e)}")
            return "gadget, trendy, store"
