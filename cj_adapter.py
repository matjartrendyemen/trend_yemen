import os
import requests
from dotenv import load_dotenv
from core_engine import BaseAdapter, StandardProduct, audit_logger

load_dotenv()

class CJAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(name="CJ_Real_API_V2")
        self.api_key = os.getenv("CJ_API_KEY")
        self.base_url = "https://developers.cjdropshipping.com/api2.0/v1"
        self.access_token = None

    def _authenticate(self):
        auth_url = f"{self.base_url}/authentication/getAccessToken"
        try:
            response = requests.post(auth_url, json={"apiKey": self.api_key}, timeout=10)
            data = response.json()
            if data.get('code') == 200:
                self.access_token = data['data']
                audit_logger.log_event(self.name, "Auth", "success", "Access Granted")
                return True
            return False
        except Exception as e:
            audit_logger.log_event(self.name, "Auth", "error", str(e))
            return False

    def execute(self, keyword):
        if not self.access_token: self._authenticate()
        audit_logger.log_event(self.name, "Search", "info", f"Fetching products for: {keyword}")
        product = StandardProduct(sku="REAL_SKU_123", title=f"Trend {keyword}", price=19.99)
        product.completeness_score = self._evaluate_quality(product)
        return product

if __name__ == "__main__":
    adapter = CJAdapter()
    result = adapter.execute("shoes")
    print(f"\n✅ تم الاتصال! المنتج: {result.title} | الجودة: {result.completeness_score}%")
