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
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image and provide 5 keywords."
        try:
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                content = [prompt, image_url]
            
            # ملاحظة: تم حذف كلمة 'models/' نهائياً هنا
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Log: {e}")
            return "gadget, trendy, store"
