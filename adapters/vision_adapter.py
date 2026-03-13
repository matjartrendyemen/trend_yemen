import os
import requests
import base64
from io import BytesIO
from google import genai
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام v1beta كما في التقرير الناجح
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            # الاسم المجرد للموديل
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # الخطوة 1: تحميل الصورة من الرابط (كما في تقريرك الناجح)
            system_log.info(f"📸 Downloading image: {image_url}")
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            
            # الخطوة 2: تحويل الصورة إلى Bytes
            img_bytes = BytesIO(response.content).getvalue()

            # الخطوة 3: إرسال الطلب كـ Inline Data (هذا ما يمنع الـ 404)
            response_ai = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Analyze this product image and return 5 precise English keywords separated by commas."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_bytes}}
                        ]
                    }
                ]
            )

            if response_ai and response_ai.text:
                keywords = response_ai.text.strip().replace("\n", " ")
                system_log.info(f"✅ Vision Success: {keywords}")
                return keywords
            
            return "gadget, trendy, store"

        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {e}")
            return "gadget, trendy, store"
