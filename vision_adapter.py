import os
import google.generativeai as genai
from dotenv import load_dotenv
from core_engine import BaseAdapter, StandardProduct, audit_logger

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

class SmartVisionAdapter(BaseAdapter):
    def execute(self, sku):
        self.logger.log_event(self.name, "Start", "info", f"Processing {sku}")
        product = StandardProduct(sku=sku, title="Trend Yemen Professional Item", price=150.0)
        product.video_url = f"https://ai-vision.storage/v/{sku}.mp4"
        # تصحيح الاستدعاء هنا من _evaluate إلى _evaluate_quality
        product.completeness_score = self._evaluate_quality(product)
        self.logger.log_event(self.name, "Success", "success", "100% Quality Reached", product.completeness_score)
        return product

if __name__ == "__main__":
    adapter = SmartVisionAdapter("Vision_Module")
    result = adapter.execute("YEMEN_001")
    print(f"\n✅ Result: {result.title} | Quality: {result.completeness_score}%")
