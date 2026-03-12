import os
import requests
from monitoring.logger import system_log

class PexelsAdapter:
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/v1/search"

    def fetch_lifestyle_images(self, keyword: str, count: int = 3) -> list:
        if not self.api_key:
            system_log.warning("PEXELS_API_KEY missing.")
            return []
            
        headers = {"Authorization": self.api_key}
        params = {"query": keyword, "per_page": count, "orientation": "square"}
        
        try:
            # الالتزام بـ timeout لضمان عدم تعليق السيرفر
            response = requests.get(self.base_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [photo['src']['large'] for photo in data.get('photos', [])]
            return []
        except Exception as e:
            system_log.error(f"❌ Pexels Fetch Error: {e}")
            return []
