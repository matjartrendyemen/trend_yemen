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
            # استخدام العميل الحديث google-genai
            self.client = genai.Client(api_key=self.api_key)
            # الحل الجذري: اسم الموديل بدون أي بادئة (Prefix)
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique and specific search keywords separated by commas."
        try:
            # محاولة جلب الصورة
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except:
                # منطق الروابط المحمية الذي صممناه سابقاً
                system_log.warning("⚠️ Using URL directly for protected link...")
                content = [prompt, image_url]
            
            # الاستدعاء الصحيح المتوافق مع v1beta
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            # صمام الأمان الذي رأيناه في صورتك للشيت (Completed)
            system_log.error(f"❌ Vision Final Error: {e}")
            return "gadget, trendy, store"
