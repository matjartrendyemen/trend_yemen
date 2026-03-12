from google import genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class VisionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # الانتقال للمكتبة المستقرة المعتمدة في تقريرنا
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique and specific search keywords separated by commas."
        try:
            # محاولة جلب الصورة ومعالجتها
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                system_log.warning("⚠️ Using URL directly for protected link...")
                content = [prompt, image_url]
            
            # الاستدعاء الحديث (بدون بادئة models/)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Analysis Error (Fixed): {e}")
            return "gadget, trendy, store"
