from adapters.vision_adapter import SmartVisionAdapter

class VisionService:
    def __init__(self):
        self.adapter = SmartVisionAdapter()

    def extract_keywords(self, image_url):
        return self.adapter.extract_keywords(image_url)
