import json
import os

from google import genai
from monitoring.logger import system_log


class SEOService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_id = "gemini-1.5-flash"

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                system_log.error(f"❌ SEOService client init error: {e}")
                self.client = None

    def _clean(self, value):
        return str(value or "").strip()

    def _join_non_empty(self, values, delimiter=" "):
        return delimiter.join([self._clean(value) for value in values if self._clean(value)])

    def _normalize_keywords(self, values):
        if isinstance(values, list):
            items = [self._clean(item) for item in values if self._clean(item)]
            return ", ".join(items)

        text = self._clean(values)
        if not text:
            return ""

        parts = [part.strip() for part in text.replace("\n", ",").split(",")]
        parts = [part for part in parts if part]
        return ", ".join(parts)

    def _normalize_hashtags(self, values):
        if isinstance(values, list):
            tags = []
            for item in values:
                text = self._clean(item)
                if not text:
                    continue
                if not text.startswith("#"):
                    text = "#" + text.replace(" ", "_")
                tags.append(text)
            return " ".join(tags)

        text = self._clean(values)
        if not text:
            return ""

        parts = text.replace("\n", " ").split()
        normalized = []
        for part in parts:
            cleaned = self._clean(part)
            if not cleaned:
                continue
            if not cleaned.startswith("#"):
                cleaned = "#" + cleaned.replace(" ", "_")
            normalized.append(cleaned)
        return " ".join(normalized)

    def _extract_first_json_object(self, text):
        raw = self._clean(text)
        if not raw:
            return None

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = raw[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None

    def _build_fallback_payload(
        self,
        product_name,
        category_id,
        manual_price,
        final_media_url,
        final_media_status,
    ):
        name = self._clean(product_name) or "منتج مميز"
        category = self._clean(category_id)
        price = self._clean(manual_price)
        has_final_media = bool(self._clean(final_media_url))
        media_status = self._clean(final_media_status) or "selected"

        marketing_title = self._join_non_empty(
            [name, "عرض مميز", "في اليمن"],
            delimiter=" | ",
        )

        category_phrase = category or "منتجات مختارة"
        media_phrase = (
            "بصورة نهائية جاهزة للعرض"
            if has_final_media
            else "بصيغة جاهزة للمراجعة"
        )

        marketing_description = (
            f"{name} من فئة {category_phrase} بسعر {price}."
            f" المنتج {media_phrase} وحالته الإعلامية الحالية: {media_status}."
            f" مناسب للعرض التسويقي والمراجعة قبل النشر."
        )

        social_post = (
            f"✨ {name}\n"
            f"💰 السعر: {price}\n"
            f"📦 الفئة: {category_phrase}\n"
            f"📸 الحالة الإعلامية: {media_status}\n"
            f"جاهز للمراجعة والنشر داخل متجر Trend Yemen."
        )

        seo_keywords = self._normalize_keywords([
            name,
            category_phrase,
            "Trend Yemen",
            "متجر يمني",
            "تسويق يمني",
        ])

        seo_hashtags = self._normalize_hashtags([
            "TrendYemen",
            "ترند_اليمن",
            name.replace(" ", "_"),
            category_phrase.replace(" ", "_"),
            "اليمن",
        ])

        return {
            "marketing_title": marketing_title,
            "marketing_description": marketing_description,
            "social_post": social_post,
            "seo_keywords": seo_keywords,
            "seo_hashtags": seo_hashtags,
            "status": "ready",
            "error_message": "",
        }

    def generate_publish_ready_content(
        self,
        product_name,
        category_id,
        manual_price,
        final_media_url,
        final_media_status,
    ):
        fallback = self._build_fallback_payload(
            product_name=product_name,
            category_id=category_id,
            manual_price=manual_price,
            final_media_url=final_media_url,
            final_media_status=final_media_status,
        )

        if not self.client:
            system_log.warning("SEOService running in fallback mode: GEMINI_API_KEY missing or client unavailable.")
            return fallback

        name = self._clean(product_name)
        category = self._clean(category_id)
        price = self._clean(manual_price)
        media_status = self._clean(final_media_status) or "selected"
        has_final_media = "yes" if self._clean(final_media_url) else "no"

        prompt = f"""
أنت تكتب مخرجات محتوى تجاري عربية موجهة لسوق يمني.
أعد النتيجة فقط كـ JSON صالح بدون أي شرح إضافي.

المدخلات:
- ProductName: {name}
- CategoryID: {category}
- ManualPrice: {price}
- FinalMediaPresent: {has_final_media}
- FinalMediaStatus: {media_status}

أخرج المفاتيح التالية فقط:
{{
  "marketing_title": "...",
  "marketing_description": "...",
  "social_post": "...",
  "seo_keywords": ["...", "..."],
  "seo_hashtags": ["#...", "#..."]
}}

قواعد:
- استخدم العربية الواضحة
- اجعل العنوان التسويقي قصيرًا نسبيًا
- اجعل الوصف مناسبًا للمراجعة والنشر
- اجعل social_post جاهزًا للنشر التجاري
- لا تخترع سعرًا مختلفًا عن السعر المعطى
- لا تضف أي حقول إضافية
""".strip()

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )

            response_text = self._clean(getattr(response, "text", ""))
            parsed = self._extract_first_json_object(response_text)

            if not isinstance(parsed, dict):
                system_log.warning(f"SEOService JSON parse fallback used for: {name}")
                return fallback

            merged = dict(fallback)
            merged["marketing_title"] = self._clean(parsed.get("marketing_title")) or fallback["marketing_title"]
            merged["marketing_description"] = self._clean(parsed.get("marketing_description")) or fallback["marketing_description"]
            merged["social_post"] = self._clean(parsed.get("social_post")) or fallback["social_post"]
            merged["seo_keywords"] = self._normalize_keywords(parsed.get("seo_keywords")) or fallback["seo_keywords"]
            merged["seo_hashtags"] = self._normalize_hashtags(parsed.get("seo_hashtags")) or fallback["seo_hashtags"]
            merged["status"] = "ready"
            merged["error_message"] = ""

            system_log.info(f"✅ Publish-ready content generated for: {name}")
            return merged

        except Exception as e:
            system_log.error(f"❌ SEOService generate_publish_ready_content error: {e}")
            return fallback

    def generate_yemeni_post(self, title: str, price_usd: float) -> dict:
        title_text = self._clean(title)

        try:
            price_value = float(price_usd)
        except Exception:
            price_value = 0.0

        fallback = {
            "price_sar": round(price_value * 3.75, 2),
            "price_yer": round(round(price_value * 3.75, 2) * 139.8, 2),
            "social_post": f"جديدنا: {title_text or 'منتج مميز'}",
        }

        if not self.client:
            return fallback

        try:
            prompt = f"""
اكتب بوست تسويقي جذاب لمنتج {title_text} لجمهور يمني.
السعر التقديري بالدولار: {price_value}.
أخرج النص فقط بدون شرح إضافي.
""".strip()

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )

            social_post = self._clean(getattr(response, "text", "")) or fallback["social_post"]

            system_log.info(f"✅ SEO generated for: {title_text}")
            return {
                "price_sar": fallback["price_sar"],
                "price_yer": fallback["price_yer"],
                "social_post": social_post,
            }
        except Exception as e:
            system_log.error(f"❌ SEO Error: {e}")
            return fallback
