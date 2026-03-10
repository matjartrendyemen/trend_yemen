def extract_keywords_from_image(model, image_url: str) -> str:
    """
    استخراج الكلمات المفتاحية من صورة باستخدام نموذج Gemini.
    """
    try:
        response = model.generate_content([f"Analyze this product image: {image_url}"])
        return response.text.strip()
    except Exception as e:
        return f"Fallback keywords due to error: {str(e)}"
