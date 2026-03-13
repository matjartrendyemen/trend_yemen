import os
import requests
import re
from io import BytesIO
from PIL import Image
from google import genai
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام v1 لضمان استقرار نموذج 2.5 فلاش في مارس 2026
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1'}
            )
            self.model_id = "gemini-2.5-flash"

    def _fix_drive_url(self, url):
        """تحويل روابط العرض في درايف لروابط تحميل بايتات الصورة"""
        if "drive.google.com" in url:
            match = re.search(r'(?:id=|[|/d/|/file/d/])([a-zA-Z0-9_-]{25,})', url)
            if match:
                return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
        return url

    def extract_keywords(self, image_url: str) -> str:
        try:
            # 1. إصلاح الرابط وإضافة Header لمنع حجب الطلب
            direct_url = self._fix_drive_url(image_url)
            system_log.info(f"📸 Fetching Image: {direct_url}")
            
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(direct_url, headers=headers, timeout=15)
            response.raise_for_status()
            img_data = response.content

            # 2. التأكد من أن البيانات هي صورة (حل خطأ cannot identify)
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # 3. إرسال الطلب لـ Gemini 2.5 Flash (Inline Data)
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    "Analyze this product and return 4 precise English keywords separated by commas.",
                    {"inline_data": {"mime_type": mime_type, "data": img_data}}
                ]
            )
            return result.text.strip().replace("\n", " ") if result.text else "gadget, trendy"
        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {str(e)}")
            return "gadget, trendy"
