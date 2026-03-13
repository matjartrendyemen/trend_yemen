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
            # استخدام v1 المستقر لنموذج 2.5 فلاش (المعتمد في تقاريرك)
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1'}
            )
            self.model_id = "gemini-2.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # إضافة User-Agent لمحاكاة المتصفح ومنع حجب Google Drive للتحميل
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # التأكد من أن الرابط مباشر (uc?id=...)
            direct_url = image_url.replace("view?usp=sharing", "uc?export=download")
            if "uc?" in direct_url and "export=download" not in direct_url:
                direct_url += "&export=download"

            system_log.info(f"📸 Decoding Image: {direct_url}")
            
            response = requests.get(direct_url, headers=headers, timeout=15)
            response.raise_for_status()
            img_data = response.content

            # التحقق من الملف عبر Pillow قبل إرساله (حل خطأ cannot identify)
            try:
                img = Image.open(BytesIO(img_data))
                mime_type = Image.MIME.get(img.format, "image/jpeg")
            except Exception:
                system_log.warning("⚠️ Warning: Data is not a direct image. Falling back to URL-only analysis.")
                return self._fallback_url_analysis(image_url)

            # بناء الطلب باستخدام inline_data (المنطق الذي نجح في rp.txt)
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

    def _fallback_url_analysis(self, url):
        """حل احتياطي في حال فشل تحميل الصورة كبايتات"""
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[f"Analyze the product in this image link: {url}"]
        )
        return res.text.strip() if res.text else "product, quality"
