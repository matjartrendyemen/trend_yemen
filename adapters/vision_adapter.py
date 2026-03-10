import requests
from io import BytesIO
from PIL import Image
from monitoring.logger import system_log

def extract_keywords_from_image(model, image_url: str) -> str:
    system_log.info(f"Downloading image for AI analysis: {image_url}")
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        prompt = "Analyze this product image. Give me 3-4 precise English search keywords suitable for e-commerce search (e.g., men running shoes). Reply ONLY with the keywords."
        
        result = model.generate_content([prompt, img])
        keywords = result.text.strip().replace('\n', ' ')
        system_log.info(f"AI Vision extracted keywords: {keywords}")
        return keywords
    except Exception as e:
        system_log.error(f"Vision Adapter Error: {e}")
        raise
