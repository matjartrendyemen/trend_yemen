import random
import re
from adapters.vision_adapter import SmartVisionAdapter


class AIService:
    def __init__(self):
        self.vision = SmartVisionAdapter()

    def process_image(self, image_url: str):
        try:
            raw_text = self.vision.extract_keywords(image_url)

            if raw_text is None:
                raise ValueError("AI response is empty")

            if not isinstance(raw_text, str):
                raw_text = str(raw_text)

            text = raw_text.strip()

            if not text:
                raise ValueError("AI response is empty")

            product_name = self._extract_product_name(text)
            product_name = self._clean_product_name(product_name)

            category_id = self._infer_category(product_name)
            sku = self._generate_sku()

            quality_status, error_message = self._evaluate_quality(product_name)

            return {
                "ProductName": product_name,
                "SKU": sku,
                "CategoryID": category_id,
                "FinalImageURL": image_url,
                "QualityStatus": quality_status,
                "ErrorMessage": error_message,
            }

        except Exception as e:
            return {
                "ProductName": "",
                "SKU": "",
                "CategoryID": "",
                "FinalImageURL": image_url,
                "QualityStatus": "Failed",
                "ErrorMessage": str(e)[:100],
            }

    # -------------------------
    # Helpers
    # -------------------------

    def _extract_product_name(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""

        for line in lines:
            lower = line.lower()
            if lower.startswith("productname:") or lower.startswith("product name:"):
                return line.split(":", 1)[1].strip()

        return lines[0]

    def _clean_product_name(self, name: str) -> str:
        if not name:
            return ""

        unwanted_words = ["product", "image", "description"]
        cleaned = name

        for word in unwanted_words:
            cleaned = re.sub(word, "", cleaned, flags=re.IGNORECASE)

        cleaned = " ".join(cleaned.split())

        if len(cleaned) > 60:
            cleaned = cleaned[:60].strip()

        return cleaned

    def _infer_category(self, name: str) -> str:
        name_lower = name.lower()

        if any(word in name_lower for word in ["shirt", "dress", "jacket", "pants", "shoes"]):
            return "fashion"

        if any(word in name_lower for word in ["phone", "laptop", "camera", "headphones", "charger"]):
            return "electronics"

        if any(word in name_lower for word in ["cream", "makeup", "perfume", "skincare", "beauty"]):
            return "beauty"

        if any(word in name_lower for word in ["sofa", "table", "chair", "lamp", "kitchen"]):
            return "home"

        return "general"

    def _generate_sku(self) -> str:
        return f"SKU-{random.randint(10000, 99999)}"

    def _evaluate_quality(self, name: str):
        if not name:
            return "NeedsReview", "Missing ProductName"

        if len(name) < 5:
            return "NeedsReview", "Too short name"

        generic_words = ["item", "thing", "object", "stuff"]
        if name.lower() in generic_words:
            return "NeedsReview", "Generic product name"

        return "Accepted", ""
