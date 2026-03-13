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
            # استخدام العميل الجديد الذي ظهر في صورة التثبيت (1.66.0)
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # 1. تحميل الصورة (نفس منطق التقرير الناجح)
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            img_bytes = BytesIO(response.content).getvalue()
            
            # 2. التأكد من نوع الصورة باستخدام Pillow
            img = Image.open(BytesIO(img_data := response.content))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # 3. إرسال الطلب (هذا هو الهيكل الذي يقبله الإصدار 1.66.0)
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Analyze this product image and return 3-4 precise English keywords."},
                            {"inline_data": {"mime_type": mime_type, "data": img_bytes}}
                        ]
                    }
                ]
            )

            if result and result.text:
                keywords = result.text.strip().replace("\n", " ")
                system_log.info(f"✅ Success: {keywords}")
                return keywords
            
            return "gadget, trendy, store"

        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {e}")
            return "gadget, trendy, store"
