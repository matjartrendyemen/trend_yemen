from adapters.vision_adapter import SmartVisionAdapter
from monitoring.logger import system_log

class VisionService:
    def __init__(self):
        # نعتمد كلياً على المحول الجديد المستقر
        self.adapter = SmartVisionAdapter()

    def extract_keywords(self, image_url: str) -> str:
        system_log.info(f"🔍 Vision Service: Processing image URL...")
        return self.adapter.extract_keywords(image_url)
