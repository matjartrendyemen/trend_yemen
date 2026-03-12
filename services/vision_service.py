from google import genai
import os
from monitoring.logger import system_log

class VisionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام العميل الحديث المعتمد في تقاريرنا
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-1.5-flash"

    def analyze_product_image(self, image_data, prompt):
        """تحليل صورة المنتج واستخراج التفاصيل للجمهور اليمني"""
        try:
            # الاستدعاء الصحيح بدون بادئة models/ لتجنب خطأ 404
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, image_data]
            )
            
            system_log.info("✅ Vision Analysis completed successfully.")
            return response.text.strip()
            
        except Exception as e:
            # نظام الرؤية الهجينة: نص بديل في حال الفشل لضمان استمرار المتجر
            system_log.error(f"❌ Vision Engine Error: {e}")
            return "gadget, trendy, store"
