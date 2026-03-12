from google import genai
import os
import requests
from PIL import Image
from io import BytesIO
from monitoring.logger import system_log

class VisionService:
    def __init__(self):
        # الاعتماد على المكتبة الحديثة لتجنب تحذيرات الأمس وأخطاء المسارات
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-1.5-flash"  # تم التأكد من حذف بادئة models/ هنا

    def extract_keywords(self, image_url: str) -> str:
        """تحليل صورة المنتج واستخراج 5 كلمات مفتاحية ذكية"""
        prompt = "Analyze this product image for an e-commerce store. Provide 5 unique and specific search keywords separated by commas."
        try:
            # محاولة معالجة الصورة فيزيائياً لزيادة دقة الـ AI
            try:
                response_img = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response_img.content))
                content = [prompt, img]
            except Exception as e:
                # في حال كانت الروابط محمية، نمرر الرابط مباشرة
                system_log.warning(f"⚠️ Using URL directly for protected link: {e}")
                content = [prompt, image_url]
            
            # الاستدعاء الحديث المتوافق مع إصدار v1beta وسيرفر Railway
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=content
            )
            
            system_log.info("✅ Vision Analysis Success.")
            return response.text.strip().replace("\n", " ")
            
        except Exception as e:
            # نظام الطوارئ (Fallback) لضمان استمرار المتجر في العمل
            system_log.error(f"❌ Vision Final Error (Fixed Logic): {e}")
            return "gadget, trendy, store"
