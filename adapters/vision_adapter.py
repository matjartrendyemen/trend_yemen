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
            # استخدام v1beta لضمان التوافق مع الخطة المجانية
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # معالجة روابط جوجل درايف لضمان التحميل المباشر
            url = image_url.replace("view?usp=sharing", "uc?export=download")
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            img_data = response.content
            # التحقق من الملف بواسطة Pillow قبل الإرسال
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # هيكل الطلب الناجح كما في تقاريرك
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
                return result.text.strip().replace("\n", " ")
            return "gadget, trendy, store"

        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {str(e)}")
            return "gadget, trendy, store"
