from google import genai
import os
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # استخدام الإصدار v1beta والعميل الحديث
            self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
            # الاسم المجرد تماماً لمنع خطأ المسار المزدوج
            self.model_id = "gemini-1.5-flash"

    def extract_keywords(self, image_url: str) -> str:
        try:
            # إرسال الرابط مباشرة للـ AI لتقليل استهلاك موارد السيرفر وضمان عدم فشل التحميل
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=["Analyze this product image for an e-commerce store. Provide 5 unique search keywords separated by commas.", image_url]
            )
            system_log.info("✅ Vision Adapter: Keywords generated successfully.")
            return response.text.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Adapter Error: {e}")
            return "gadget, trendy, store"
