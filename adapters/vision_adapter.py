import google.generativeai as genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique and specific search keywords separated by commas."
        try:
            try:
                # محاولة تحميل الصورة كملف لضمان أعلى دقة
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                # احتياطي لروابط درايف المحمية
                system_log.warning("⚠️ Using URL directly for protected link...")
                content = [prompt, image_url]
            
            response = self.model.generate_content(content)
            return response.text.strip().replace("\n", " ") if response else "gadget, trendy, store"
        except Exception as e:
            system_log.error(f"❌ Vision Analysis Error: {e}")
            return "gadget, trendy, store"
