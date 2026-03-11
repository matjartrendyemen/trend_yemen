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
        # نستخدم الموديل المستقر الذي أثبت نجاحه معك
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_keywords(self, image_url: str) -> str:
        try:
            # 1. تحميل الصورة برمجياً لضمان عدم حدوث خطأ 404 في الروابط
            response_img = requests.get(image_url, timeout=15)
            img = Image.open(BytesIO(response_img.content))

            # 2. الـ Prompt الاحترافي الذي استخدمته بالأمس
            prompt = """
            Analyze this product image for an e-commerce store. 
            Provide 5 unique and specific search keywords separated by commas.
            Focus on the product type, color, and key features.
            Do not use generic words like 'trending' unless it truly fits.
            Example: 'wireless headphones, black matte, noise canceling, tech, audio'
            """
            
            # 3. إرسال الصورة ككائن (Object) وليس كرابط لتجنب مشاكل الـ API
            response = self.model.generate_content([prompt, img])
            
            if response and response.text:
                keywords = response.text.strip().replace("\n", " ")
                system_log.info(f"✨ AI Analysis Success: {keywords}")
                return keywords
            return "gadget, trendy, store"
            
        except Exception as e:
            system_log.error(f"❌ Vision Analysis Error: {e}")
            return "product, trend, store"
