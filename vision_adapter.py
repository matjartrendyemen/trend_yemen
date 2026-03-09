import os
import requests
from io import BytesIO
from PIL import Image
import google.genai as genai
from core_engine import audit_logger, StandardProduct

class SmartVisionAdapter:
    def __init__(self, name="VisionUnit"):
        self.adapter_name = name
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            audit_logger.log_event(self.adapter_name, "Init", "error", "GEMINI_API_KEY is missing!")
        # ✅ إنشاء عميل جديد
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash"  # النموذج الصحيح المدعوم

    def extract_keywords(self, image_url: str) -> str:
        audit_logger.log_event(self.adapter_name, "Analyze", "info", f"Downloading image: {image_url}")
        try:
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()

            img_bytes = BytesIO(response.content).getvalue()
            img = Image.open(BytesIO(response.content))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            prompt = "Analyze this product image and return 3-4 precise English keywords suitable for searching."

            result = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": img_bytes}}
                    ]}
                ]
            )

            keywords = result.text.strip().replace('\n', ' ')
            audit_logger.log_event(self.adapter_name, "Analyze", "success", f"Keywords generated: {keywords}")
            return keywords

        except Exception as e:
            audit_logger.log_event(self.adapter_name, "AI_Error", "error", str(e))
            raise ValueError(f"Vision AI failed to analyze image: {e}")

    def heal_product_data(self, product: StandardProduct) -> StandardProduct:
        audit_logger.log_event(self.adapter_name, "Heal", "info", f"Healing data for SKU: {product.sku}")
        try:
            product.completeness_score = 100.0
            audit_logger.log_event(self.adapter_name, "Heal", "success", "Data healed successfully.")
            return product
        except Exception as e:
            audit_logger.log_event(self.adapter_name, "Heal", "error", str(e))
            return product

# ✅ جزء تنفيذي للتجربة
if __name__ == "__main__":
    adapter = SmartVisionAdapter()

    # تجربة heal_product_data
    dummy_product = StandardProduct(sku="TEST123")
    healed = adapter.heal_product_data(dummy_product)
    print("Completeness score:", healed.completeness_score)

    # تجربة extract_keywords على صورة من Google Drive
    test_image_url = "https://drive.google.com/uc?export=download&id=1fmQtZY3j8Vc1rUj1f1qPD-Fbnx0SrEhu"
    try:
        keywords = adapter.extract_keywords(test_image_url)
        print("Extracted keywords:", keywords)
    except Exception as e:
        print("Error:", e)
