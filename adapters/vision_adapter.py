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
            # استخدام v1 المستقر لنموذج 2.5 فلاش
            self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1'})
            self.model_id = "gemini-2.5-flash"

    def _get_direct_link(self, url):
        """تحويل روابط العرض في درايف إلى روابط تحميل مباشرة"""
        if "drive.google.com" in url:
            file_id = ""
            if "/d/" in url: file_id = url.split("/d/").[1]split("/")
            elif "id=" in url: file_id = url.split("id=").[1]split("&")
            if file_id: return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url

    def extract_keywords(self, image_url: str) -> str:
        try:
            # 1. إصلاح الرابط وإضافة Header لمحاكاة المتصفح
            direct_url = self._get_direct_link(image_url)
            system_log.info(f"📸 Fetching Raw Image: {direct_url}")
            
            response = requests.get(direct_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            response.raise_for_status()
            img_data = response.content

            # 2. التحقق من الصورة (Pillow)
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # 3. إرسال البيانات كبايتات (Inline Data) لضمان النجاح
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
