import os
import requests
import time
from monitoring.logger import system_log

class CJAdapter:
    def __init__(self):
        self.base_url = "https://developers.cjdropshipping.com/api2.0/v1"
        self.api_key = os.getenv("CJ_API_KEY")
        self.access_token = None
        self.token_expiry = 0

    def _authenticate(self):
        current_time = time.time()
        if self.access_token and current_time < self.token_expiry:
            return True

        if not self.api_key:
            system_log.error("❌ CJ_API_KEY is missing in Railway variables!")
            return False

        system_log.info("🔐 Security: Authenticating with API Key...")
        auth_url = f"{self.base_url}/authentication/getAccessToken"
        try:
            response = requests.post(auth_url, json={"apiKey": self.api_key}, timeout=15)
            data = response.json()
            if data.get('result') == True:
                self.access_token = data['data']['accessToken']
                self.token_expiry = current_time + 36000
                system_log.info("✅ CJ Authentication Success.")
                return True
            else:
                system_log.error(f"❌ CJ Auth Failed: {data.get('message')}")
                return False
        except Exception as e:
            system_log.error(f"📡 CJ Connection Error: {e}")
            return False

    def fetch_product(self, keyword: str) -> dict:
        if not self._authenticate():
            raise ValueError("CJ Auth Failed.")
        
        search_url = f"{self.base_url}/product/list"
        headers = {"CJ-Access-Token": self.access_token}
        params = {"keyword": keyword, "pageSize": 1}
        
        try:
            res = requests.get(search_url, headers=headers, params=params, timeout=20).json()
            if res.get('result') and res['data']['list']:
                item = res['data']['list'][0]
                return {
                    "sku": item.get('productSku'),
                    "title": item.get('productNameEn'),
                    "price": item.get('sellPrice'),
                    "image": item.get('productImage')
                }
            raise ValueError(f"No match for: {keyword}")
        except Exception as e:
            system_log.error(f"❌ CJ Fetch Error: {e}")
            raise
