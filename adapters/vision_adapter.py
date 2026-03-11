import google.generativeai as genai
import os
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_keywords(self, image_url: str) -> str:
        try:
            # طلب تحليل دقيق ومختلف لكل صورة
            prompt = """
            Analyze this product image for an e-commerce store. 
            Provide 5 unique and specific search keywords separated by commas.
            Focus on the product type, color, and key features.
            Do not use generic words like 'trending' unless it truly fits.
            Example: 'wireless headphones, black matte, noise canceling, tech, audio'
            """
            
            # محاولة جلب الصورة وتحليلها
            # ملاحظة: إذا كان الرابط من جوجل درايف، يفضل أن يكون رابطاً مباشراً
            response = self.model.generate_content([prompt, image_url])
            
            if response and response.text:
                keywords = response.text.strip().replace("\n", " ")
                system_log.info(f"✨ AI Analysis Success: {keywords}")
                return keywords
            return "gadget, trendy, store"
        except Exception as e:
            system_log.error(f"❌ Vision Analysis Error: {e}")
            return "error, check, link"
