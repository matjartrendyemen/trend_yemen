import requests
from monitoring.logger import system_log

class CJAdapter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cjdropshipping.com/v2"

    def get_products(self, keyword: str):
        try:
            response = requests.get(
                f"{self.base_url}/products/search",
                params={"keyword": keyword},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            system_log.error(f"CJAdapter failed: {e}")
            return {}
