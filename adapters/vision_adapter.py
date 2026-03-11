import os
import time
from google import genai
from PIL import Image
import requests
from io import BytesIO
from monitoring.logger import system_log

class SmartVisionAdapter:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.0-flash" 

    def extract_keywords(self, image_url: str):
        # محاولة الطلب حتى 3 مرات في حال حدوث ضغط (Quota)
        for attempt in range(3):
            try:
                if "drive.google.com" in image_url:
                    if "file/d/" in image_url:
                        file_id = image_url.split("file/d/")[1].split("/")[0]
                        image_url = f"https://docs.google.com/uc?export=download&id={file_id}"

                response = requests.get(image_url, timeout=15)
                img = Image.open(BytesIO(response.content))
                
                res = self.client.models.generate_content(
                    model=self.model_id,
                    contents=["Extract 3-5 core English keywords for this product. Return only keywords separated by commas.", img]
                )
                return res.text.strip()

            except Exception as e:
                if "429" in str(e):
                    system_log.warning(f"⚠️ Quota hit (Attempt {attempt+1}). Sleeping 70s...")
                    time.sleep(70) # انتظر أكثر من دقيقة لتصفير عداد جوجل
                    continue
                system_log.error(f"❌ Vision Error: {e}")
                return "trending, gadget"
        return "trending, gadget"
