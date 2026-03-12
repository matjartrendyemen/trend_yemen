from google import genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # الحل القاطع: v1beta والاسم المجرد تماماً
            self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url):
        prompt = "Analyze this product image for 5 unique search keywords."
        try:
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                content = [prompt, image_url]
            
            response = self.client.models.generate_content(model=self.model_id, contents=content)
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Final Diagnosis: {e}")
            return "gadget, trendy, store"
