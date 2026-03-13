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
            # العميل المتوافق مع الخطة المجانية وv1beta
            self.client = genai.Client(
                api_key=self.api_key, 
                http_options={'api_version': 'v1beta'}
            )
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # معالجة روابط الدرايف لتكون مباشرة
            url = image_url.replace("view?usp=sharing", "uc?export=download")
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            # الهيكل الذي نجح في تقرير rp.txt
            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": "Give me 4 English keywords for this product separated by commas."},
                            {"inline_data": {"mime_type": mime_type, "data": img_data}}
                        ]
                    }
                ]
            )

            if result and result.text:
                return result.text.strip().replace("\n", " ")
            return "gadget, trendy, store"

        except Exception as e:
            system_log.error(f"❌ Vision Error: {str(e)}")
            return "gadget, trendy, store"
