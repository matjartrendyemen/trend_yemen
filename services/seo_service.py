from google import genai
import os
from monitoring.logger import system_log

class SEOService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            # الاعتماد على المكتبة الحديثة google-genai
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-1.5-flash"

    def generate_yemeni_post(self, title: str, price_usd: float) -> dict:
        try:
            # معادلة التحويل: دولار -> سعودي (3.75) ثم سعودي -> يمني (139.8)
            price_sar = round(float(price_usd) * 3.75, 2)
            price_yer = round(price_sar * 139.8, 2)

            prompt = f"""
            اكتب بوست تسويقي جذاب لمنتج {title} لجمهور يمني.
            السعر: {price_sar} ريال سعودي ({price_yer} ريال يمني).
            توصيل لـ: صنعاء، عدن، تعز.
            هاشتاقات: #ترند_اليمن #صنعاء #عدن.
            """
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            system_log.info(f"✅ SEO generated for: {title}")
            return {
                "price_sar": price_sar,
                "price_yer": price_yer,
                "social_post": response.text.strip()
            }
        except Exception as e:
            system_log.error(f"❌ SEO Error: {e}")
            return {"price_sar": price_sar, "price_yer": price_yer, "social_post": f"جديدنا: {title}"}
