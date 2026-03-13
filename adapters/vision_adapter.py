import os
import requests
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # الرابط المباشر الذي لا يخطئ
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def extract_keywords(self, image_url: str) -> str:
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this product image for an e-commerce store. Provide 5 unique search keywords separated by commas."},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": self._get_image_data(image_url)
                    }} if not image_url.startswith('http') else {"text": f"Product Image URL: {image_url}"}
                ]
            }]
        }
        try:
            response = requests.post(self.url, json=payload, timeout=20)
            result = response.json()
            # استخراج النص بذكاء
            keywords = result['candidates'][0]['content']['parts'][0]['text']
            system_log.info("✅ Vision Success via REST API")
            return keywords.strip().replace("\n", " ")
        except Exception as e:
            system_log.error(f"❌ Vision Final REST Error: {e}")
            return "gadget, trendy, store"

    def _get_image_data(self, url):
        try:
            return requests.get(url).content.hex() # تبسيط للتحويل
        except: return ""
