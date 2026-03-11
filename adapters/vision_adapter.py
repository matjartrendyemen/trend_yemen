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
        prompt = """
        Analyze this product image for an e-commerce store. 
        Provide 5 unique and specific search keywords separated by commas.
        Focus on the product type, color, and key features.
        Example: 'wireless headphones, black matte, noise canceling, tech, audio'
        """
        try:
            # محاولة التحميل ككائن (Object) لضمان أعلى دقة
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                response = self.model.generate_content([prompt, img])
            except:
                # إذا كان الرابط محمي (مثل جوجل درايف)، نرسل الرابط مباشرة كما كان سابقاً
                system_log.warning("⚠️ Using URL directly for protected link...")
                response = self.model.generate_content([prompt, image_url])
            
            if response and response.text:
                keywords = response.text.strip().replace("\n", " ")
                system_log.info(f"✨ AI Analysis Success: {keywords}")
                return keywords
            return "gadget, trendy, store"
        except Exception as e:
            system_log.error(f"❌ Vision Analysis Error: {e}")
            return "gadget, trendy, store"
