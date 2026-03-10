import os
from google import genai
from PIL import Image
import requests
from io import BytesIO
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        # استخدام العميل الجديد والموديل الناجح حسب التقرير
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.0-flash" 

    def extract_keywords(self, image_url: str):
        try:
            system_log.info(f"📸 AI Analyzing image: {image_url}")
            
            # معالجة روابط Google Drive لتحويلها لروابط تحميل مباشرة
            if "drive.google.com" in image_url:
                if "file/d/" in image_url:
                    file_id = image_url.split("file/d/")[1].split("/")[0]
                    image_url = f"https://docs.google.com/uc?export=download&id={file_id}"

            response = requests.get(image_url, timeout=15)
            img = Image.open(BytesIO(response.content))
            
            # تنفيذ الاستعلام بالنموذج السريع الحديث
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=["Extract 3-5 core English keywords for this product. Return only keywords separated by commas.", img]
            )
            
            keywords = response.text.strip()
            system_log.info(f"✨ AI Result: {keywords}")
            return keywords
        except Exception as e:
            system_log.error(f"❌ Vision Error: {e}")
            return "trending, gadget, high-quality"
