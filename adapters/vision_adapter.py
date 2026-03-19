import os
import requests
import re
from io import BytesIO
from PIL import Image
from google import genai
from monitoring.logger import system_log


class SmartVisionAdapter:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        self.client = genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1"}
        )
        self.model_id = "gemini-2.5-flash"

    def _get_direct_url(self, url):
        if "drive.google.com" in url:
            match = re.search(r'(?:id=|/d/|/file/d/)([a-zA-Z0-9_-]{25,})', url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url

    def extract_keywords(self, image_url: str) -> str:
        try:
            direct_url = self._get_direct_url(image_url)
            headers = {"User-Agent": "Mozilla/5.0"}

            system_log.info(f"📸 Fetching Image: {direct_url}")

            response = requests.get(direct_url, headers=headers, timeout=15)
            response.raise_for_status()

            img_data = response.content

            img = Image.open(BytesIO(img_data))
            mime_type = Image.MIME.get(img.format, "image/jpeg")

            result = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    "Analyze this product and return 5 precise English keywords separated by commas.",
                    {"inline_data": {"mime_type": mime_type, "data": img_data}}
                ]
            )

            if not result.text or not result.text.strip():
                raise ValueError("Gemini returned empty response")

            return result.text.strip().replace("\n", " ")

        except Exception as e:
            system_log.error(f"❌ Vision Final Error: {str(e)}")
            raise
