from datetime import datetime, timezone

from services.seo_service import SEOService


class ContentOutputService:
    ELIGIBLE_FINAL_MEDIA_STATUSES = {
        "selected",
        "ready",
        "approved",
        "finalized",
    }

    READY_CONTENT_STATUSES = {
        "ready",
    }

    def __init__(self, sheets_store, seo_service=None):
        self.sheets = sheets_store
        self.seo = seo_service or SEOService()

    @staticmethod
    def _clean(value):
        return str(value or "").strip()

    @classmethod
    def _first_non_empty(cls, *values):
        for value in values:
            cleaned = cls._clean(value)
            if cleaned:
                return cleaned
        return ""

    @classmethod
    def build_eligibility_snapshot(cls, record):
        processing_status = cls._first_non_empty(
            record.get("ProcessingStatus"),
            record.get("processing_status"),
        )
        product_name = cls._first_non_empty(
            record.get("ProductName"),
            record.get("product_name"),
            record.get("Name"),
            record.get("name"),
            record.get("title"),
        )
        category_id = cls._first_non_empty(
            record.get("CategoryID"),
            record.get("category_id"),
            record.get("Category"),
            record.get("category"),
        )
        manual_price = cls._first_non_empty(
            record.get("Price"),
            record.get("price"),
        )
        final_primary_media_url = cls._first_non_empty(
            record.get("FinalPrimaryMediaURL"),
            record.get("final_primary_media_url"),
            record.get("FinalImageURL"),
            record.get("final_image_url"),
        )
        final_media_status = cls._first_non_empty(
            record.get("FinalMediaStatus"),
            record.get("final_media_status"),
        )

        checks = {
            "has_completed_processing": processing_status == "Completed",
            "has_product_name": bool(product_name),
            "has_price": bool(manual_price),
            "has_final_primary_media_url": bool(final_primary_media_url),
            "final_media_status_ok": final_media_status.lower() in cls.ELIGIBLE_FINAL_MEDIA_STATUSES,
        }

        is_eligible = all(checks.values())

        reasons = []
        if not checks["has_completed_processing"]:
            reasons.append("ProcessingStatus must be Completed")
        if not checks["has_product_name"]:
            reasons.append("ProductName is missing")
        if not checks["has_price"]:
            reasons.append("Price is missing")
        if not checks["has_final_primary_media_url"]:
            reasons.append("FinalPrimaryMediaURL is missing")
        if not checks["final_media_status_ok"]:
            reasons.append("FinalMediaStatus is not eligible")

        return {
            "is_eligible": is_eligible,
            "reason": "Eligible for content generation" if is_eligible else "; ".join(reasons),
            "processing_status": processing_status,
            "product_name": product_name,
            "category_id": category_id,
            "manual_price": manual_price,
            "final_primary_media_url": final_primary_media_url,
            "final_media_status": final_media_status,
            **checks,
        }

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _get_row_by_id(self, row_id):
        rows = self.sheets._get_all_records()
        for row in rows:
            if self._clean(row.get("RowID")) == self._clean(row_id):
                return row
        return None

    def generate_for_row_id(self, row_id):
        normalized_row_id = self._clean(row_id)
        if not normalized_row_id:
            raise ValueError("Missing RowID")

        row = self._get_row_by_id(normalized_row_id)
        if not row:
            raise ValueError("Row not found")

        eligibility = self.build_eligibility_snapshot(row)
        if not eligibility["is_eligible"]:
            raise ValueError(eligibility["reason"])

        try:
            content_payload = self.seo.generate_publish_ready_content(
                product_name=eligibility["product_name"],
                category_id=eligibility["category_id"],
                manual_price=eligibility["manual_price"],
                final_media_url=eligibility["final_primary_media_url"],
                final_media_status=eligibility["final_media_status"],
            )
        except Exception as e:
            self.sheets.update_content_fields(
                normalized_row_id,
                {
                    "ContentStatus": "failed",
                    "ContentReadyAt": "",
                    "ContentErrorMessage": str(e),
                },
            )
            return {
                "row_id": normalized_row_id,
                "content_status": "failed",
                "content_ready_at": "",
                "error_message": str(e),
            }

        status = self._clean(content_payload.get("status")) or "ready"
        error_message = self._clean(content_payload.get("error_message"))

        if status != "ready":
            self.sheets.update_content_fields(
                normalized_row_id,
                {
                    "ContentStatus": "failed",
                    "ContentReadyAt": "",
                    "ContentErrorMessage": error_message or "Content generation failed",
                },
            )
            return {
                "row_id": normalized_row_id,
                "content_status": "failed",
                "content_ready_at": "",
                "error_message": error_message or "Content generation failed",
            }

        ready_at = self._now_iso()
        self.sheets.update_content_fields(
            normalized_row_id,
            {
                "MarketingTitle": content_payload.get("marketing_title", ""),
                "MarketingDescription": content_payload.get("marketing_description", ""),
                "SocialPost": content_payload.get("social_post", ""),
                "SEOKeywords": content_payload.get("seo_keywords", ""),
                "SEOHashtags": content_payload.get("seo_hashtags", ""),
                "ContentStatus": "ready",
                "ContentReadyAt": ready_at,
                "ContentErrorMessage": "",
            },
        )

        return {
            "row_id": normalized_row_id,
            "content_status": "ready",
            "content_ready_at": ready_at,
            "marketing_title": self._clean(content_payload.get("marketing_title")),
        }
