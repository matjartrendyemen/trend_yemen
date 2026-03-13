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
            # إجبار النظام على v1 المستقر بدلاً من v1beta لضمان عدم ظهور 404
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={'api_version': 'v1'}
            )
            # استخدام Gemini 2.5 Flash كونه الموديل النشط والمستقر
            self.model_id = "gemini-2.5-flash"

    def _fix_drive_url(self, url):
        """تحويل روابط المعاينة في درايف لروابط تحميل بايتات الصورة مباشرة"""
        if "drive.google.com" in url:
            # استخراج المعرف ID سواء كان الرابط يحتوي على /d/ أو id=
            file_id_match = re.search(r'(?:id=|[|/d/|/file/d/])([a-zA-Z0-9_-]{25,})', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url

    def extract_keywords(self, image_url: str) -> str:
        try:
            # 1. إصلاح الرابط وإضافة Header لمحاكاة المتصفح لمنع حجب جوجل
            direct_url = self._fix_drive_url(image_url)
            headers = {"User-Agent": "Mozilla/5.0"}
            system_log.info(f"📸 Decoding Image from: {direct_url}")
            
            response = requests.get(direct_url, headers=headers, timeout=15)
            response.raise_for_status()
            img_content = response.content

            # 2. التحقق من أن الملف صورة حقيقية قبل إرساله
            img = Image.open(BytesIO(img_content))
            mime_type = Image.MIME.get(img.format, "image/jpeg")
            
            # 3. إرسال الطلب لنموذج 2.5 فلاش باستخدام بايتات الصورة (Inline Data)
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    "Analyze this product and return 4 precise English keywords separated by commas.",
                    {"inline_data": {"mime_type": mime_type, "data": img_content}}
                ]
            )

            if result and result.text:
                keywords = result.text.strip().replace("\n", " ")
                system_log.info(f"✅ AI Analysis Success: {keywords}")
                return keywords
            return "product, quality, store"

        except Exception as e:
            system_log.error(f"❌ Vision Execution Error: {str(e)}")
            return "gadget, trendy, store"
