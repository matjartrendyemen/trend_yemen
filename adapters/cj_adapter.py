import os
import requests
import time
from monitoring.logger import system_log

class CJAdapter:
    def __init__(self):
        self.base_url = "https://developers.cjdropshipping.com/api2.0/v1"
        self.email = os.getenv("CJ_EMAIL")
        self.password = os.getenv("CJ_PASSWORD")
        self.access_token = None
        self.token_expiry = 0

    def _authenticate(self):
        current_time = time.time()
        if self.access_token and current_time < self.token_expiry:
            return True

        system_log.info(f"🔐 Attempting Auth for: {self.email}")
        auth_url = f"{self.base_url}/authentication/getAccessToken"
        payload = {"email": self.email, "password": self.password}
        
        try:
            response = requests.post(auth_url, json=payload, timeout=15)
            
            # إذا استمر الحظر، سنقوم بطباعة رسالة واضحة
            if response.status_code == 429:
                system_log.critical("⚠️ CJ still blocking us. Wait 5 mins...")
                return False

            data = response.json()
            if data.get('result') == True:
                self.access_token = data['data']['accessToken']
                self.token_expiry = current_time + 36000
                system_log.info("✅ CJ Authentication Success.")
                return True
            else:
                # هنا سيخبرنا السجل بالسبب الحقيقي (مثلاً: Password Error)
                system_log.error(f"❌ CJ Rejected Auth: {data.get('message')}")
                return False
        except Exception as e:
            system_log.error(f"📡 CJ Connection Error: {e}")
            return False

    def fetch_product(self, keyword: str) -> dict:
        if not self._authenticate():
            raise ValueError("CJ Auth Failed. Please check Email/Password in Railway.")
        
        search_url = f"{self.base_url}/product/list"
        headers = {"CJ-Access-Token": self.access_token}
        params = {"keyword": keyword, "pageSize": 1}
        
        response = requests.get(search_url, headers=headers, params=params, timeout=20)
        res_data = response.json()
        
        if res_data.get('result') and len(res_data['data']['list']) > 0:
            item = res_data['data']['list'][0]
            return {
                "sku": item.get('productSku'),
                "title": item.get('productNameEn'),
                "price": item.get('sellPrice'),
                "image": item.get('productImage')
            }
        raise ValueError(f"No match for: {keyword}")
