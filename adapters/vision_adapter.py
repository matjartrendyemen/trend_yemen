import os
import requests
from io import BytesIO
from PIL import Image
import google.genai as genai
from monitoring.logger import system_log

def extract_keywords_from_image(model_name, image_url: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        system_log.error("GEMINI_API_KEY is missing!")
        return "Trending"
        
    client = genai.Client(api_key=api_key)
    try:
        system_log.info(f"AI Analyzing image: {image_url}")
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        prompt = "Analyze this product image and return 3-4 precise English keywords for e-commerce search."
        
        result = client.models.generate_content(
            model=model_name,
            contents=[prompt, img]
        )
        return result.text.strip().replace('\n', ' ')
    except Exception as e:
        system_log.error(f"Vision AI Error: {e}")
        raise
