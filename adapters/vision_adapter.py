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
            # استخدام v1 المستقر لنموذج 2.5 فلاش
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1'}
            )
            self.model_id = "gemini-2.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # تحويل الرابط لضمان التحميل المباشر من جوجل درايف
            url = image_url.replace("view?usp=sharing", "uc?export=download")
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            img_data = response.content

            # التأكد من صحة الملف عبر Pillow (حل خطأ cannot identify)
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # بناء الطلب بنفس الهيكل الذي أثبت نجاحه في تقرير 9 مارس
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
            return result.text.strip().replace("\n", " ") if result.text else "gadget, trendy"
        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {str(e)}")
            return "gadget, trendy"
