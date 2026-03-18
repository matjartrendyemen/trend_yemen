import os
from adapters.vision_adapter import SmartVisionAdapter
from monitoring.logger import system_log


class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if self.api_key:
            self.vision = SmartVisionAdapter()
            self.ai_available = True
            system_log.info("✅ AI Service Initialized Successfully.")
        else:
            self.ai_available = False

    def process_image(self, image_url: str):
        try:
            if not self.ai_available:
                raise ValueError("AI is not available")

            raw_text = self.vision.extract_keywords(image_url)

            if raw_text is None:
                raise ValueError("AI response is empty")

            if not isinstance(raw_text, str):
                raw_text = str(raw_text)

            text = raw_text.strip()

            if not text:
                raise ValueError("AI response is empty")

            product_name = self._extract_product_name(text)

            quality_status = "Accepted"
            error_message = ""

            if not product_name or len(product_name.strip()) < 5:
                quality_status = "NeedsReview"
                error_message = "Weak or missing ProductName"

            return {
                "ProductName": product_name,
                "SKU": f"SKU-{abs(hash(image_url)) % 100000}",
                "CategoryID": "general",
                "FinalImageURL": image_url,
                "QualityStatus": quality_status,
                "ErrorMessage": error_message,
            }

        except Exception as e:
            system_log.error(f"AI processing failed: {e}")
            return {
                "ProductName": "",
                "SKU": "",
                "CategoryID": "",
                "FinalImageURL": image_url,
                "QualityStatus": "Failed",
                "ErrorMessage": str(e),
            }

    def _extract_product_name(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if not lines:
            return ""

        for line in lines:
            normalized = line.lower()
            if normalized.startswith("productname:"):
                return line.split(":", 1)[1].strip()
            if normalized.startswith("product name:"):
                return line.split(":", 1)[1].strip()

        return lines[0].strip()
