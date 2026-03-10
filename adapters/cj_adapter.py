import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from monitoring.logger import system_log

class CJAdapter:
    def __init__(self):
        self.base_url = "https://developers.cjdropshipping.com/api2.0/v1"
        self.email = os.getenv("CJ_EMAIL")
        self.password = os.getenv("CJ_PASSWORD")
        self.access_token = None
        self._authenticate()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _authenticate(self):
        system_log.info("Authenticating with CJ Dropshipping...")
        auth_url = f"{self.base_url}/authentication/getAccessToken"
        payload = {"email": self.email, "password": self.password}
        response = requests.post(auth_url, json=payload, timeout=15)
        response.raise_for_status()
        
        if response.json().get('result'):
            self.access_token = response.json()['data']['accessToken']
            system_log.info("CJ Token acquired securely.")
        else:
            raise ValueError(f"CJ Auth failed: {response.text}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_product(self, keyword: str) -> dict:
        system_log.info(f"Searching CJ for: {keyword}")
        if not self.access_token:
            self._authenticate()

        search_url = f"{self.base_url}/product/list"
        headers = {"CJ-Access-Token": self.access_token, "Content-Type": "application/json"}
        payload = {"keyword": keyword, "page": 1, "size": 1}

        response = requests.get(search_url, headers=headers, params=payload, timeout=20)
        response.raise_for_status()
        
        res_data = response.json()
        if res_data.get('result') and res_data.get('data') and len(res_data['data']['list']) > 0:
            raw_product = res_data['data']['list'][0]
            system_log.info(f"Found CJ product: {raw_product.get('productSku')}")
            return {
                "sku": raw_product.get('productSku', 'UNKNOWN'),
                "title": raw_product.get('productNameEn', ''),
                "price": float(str(raw_product.get('sellPrice', 0)).split('-')[0]),
                "image": raw_product.get('productImage', '')
            }
        else:
            raise ValueError("No products found for this keyword in CJ.")
