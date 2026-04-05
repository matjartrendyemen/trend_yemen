# services/media_matching_service.py

import json
from datetime import datetime, timezone


class MediaMatchingService:
    def __init__(self, sheets_store):
        self.sheets = sheets_store

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _build_candidates(self, product_name, category_id):
        name = (product_name or "").strip()
        category = (category_id or "").strip()

        base_terms = [term for term in [name, category] if term]
        label_base = " - ".join(base_terms) if base_terms else "Generic Product"

        candidates = [
            {
                "type": "image",
                "url": f"dummy://media/{self._slugify(name or 'product')}-primary.jpg",
                "score": 0.92,
                "label": f"{label_base} Primary",
                "source_tag": "dummy_matcher",
                "rank": 1,
            },
            {
                "type": "image",
                "url": f"dummy://media/{self._slugify(name or 'product')}-alt-1.jpg",
                "score": 0.84,
                "label": f"{label_base} Alt 1",
                "source_tag": "dummy_matcher",
                "rank": 2,
            },
            {
                "type": "image",
                "url": f"dummy://media/{self._slugify(category or 'category')}-alt-2.jpg",
                "score": 0.76,
                "label": f"{label_base} Alt 2",
                "source_tag": "dummy_matcher",
                "rank": 3,
            },
        ]

        return candidates

    def _slugify(self, value):
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value))
        while "--" in safe:
            safe = safe.replace("--", "-")
        return safe.strip("-") or "item"

    def generate_candidates_for_row(self, row_id, product_name="", category_id=""):
        candidates = self._build_candidates(product_name, category_id)

        self.sheets.update_media_fields(
            row_id,
            {
                "MatchedMediaJSON": json.dumps(candidates, ensure_ascii=False),
                "MatchedMediaCount": len(candidates),
                "MatchedMediaStatus": "ready" if candidates else "empty",
                "MatchedAt": self._now_iso(),
            },
        )

        return {
            "row_id": row_id,
            "matched_count": len(candidates),
            "matched_status": "ready" if candidates else "empty",
        }

    def generate_candidates_for_product_record(self, record):
        row_id = str(record.get("RowID") or record.get("row_id") or "").strip()
        if not row_id:
            raise ValueError("Missing RowID")

        product_name = (
            record.get("ProductName")
            or record.get("product_name")
            or record.get("Name")
            or ""
        )
        category_id = (
            record.get("CategoryID")
            or record.get("category_id")
            or record.get("Category")
            or ""
        )

        return self.generate_candidates_for_row(
            row_id=row_id,
            product_name=product_name,
            category_id=category_id,
        )

    def generate_candidates_for_all_completed(self):
        rows = self.sheets._get_all_records()
        results = []

        for row in rows:
            row_id = str(row.get("RowID", "")).strip()
            status = str(row.get("ProcessingStatus", "")).strip().lower()

            if not row_id or status != "completed":
                continue

            results.append(self.generate_candidates_for_product_record(row))

        return results
