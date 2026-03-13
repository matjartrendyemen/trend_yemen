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
            # استخدام v1beta المتوافق مع إصدار 1.66.0 المثبت عندك
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # تنظيف الرابط لضمان أنه مباشر (خصوصاً روابط جوجل درايف)
            direct_url = image_url.replace("view?usp=sharing", "uc?export=download")
            if "drive.google.com" in direct_url and "uc?" not in direct_url:
                 # إذا كان رابط d/ تحويله لـ uc لضمان القبول
                 import re
                 match = re.search(r'/d/([^/]+)', direct_url)
                 if match:
                     direct_url = f"https://drive.google.com/uc?export=download&id={match.group(1)}"

            system_log.info(f"📸 Fetching direct image: {direct_url}")
            
            # محاولة جلب الصورة
            response = requests.get(direct_url, timeout=15)
            response.raise_for_status()
            img_data = response.content

            # التحقق من أن البيانات صورة فعلاً بواسطة Pillow
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # إرسال البيانات كـ Inline Data (هذا يحل الـ 404 والتعرف على الملف)
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Analyze this product and give 4 short English keywords separated by commas."},
                            {"inline_data": {"mime_type": mime_type, "data": img_data}}
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
            system_log.error(f"❌ Vision Final Error: {str(e)}")
            return "gadget, trendy, store"
