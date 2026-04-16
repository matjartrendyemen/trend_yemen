# services/media_matching_service.py

import json
from datetime import datetime, timezone


class MediaMatchingService:
    def __init__(self, sheets_store):
        self.sheets = sheets_store

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _clean_str(self, value):
        return str(value or "").strip()

    def _first_non_empty(self, *values):
        for value in values:
            cleaned = self._clean_str(value)
            if cleaned:
                return cleaned
        return ""

    def _build_candidates(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)

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
        normalized_row_id = self._clean_str(row_id)
        if not normalized_row_id:
            raise ValueError("Missing RowID")

        normalized_product_name = self._clean_str(product_name)
        normalized_category_id = self._clean_str(category_id)

        candidates = self._build_candidates(normalized_product_name, normalized_category_id)

        self.sheets.update_media_fields(
            normalized_row_id,
            {
                "MatchedMediaJSON": json.dumps(candidates, ensure_ascii=False),
                "MatchedMediaCount": len(candidates),
                "MatchedMediaStatus": "ready" if candidates else "empty",
                "MatchedAt": self._now_iso(),
            },
        )

        return {
            "row_id": normalized_row_id,
            "matched_count": len(candidates),
            "matched_status": "ready" if candidates else "empty",
        }

    def generate_candidates_for_product_record(self, record):
        if not isinstance(record, dict):
            raise ValueError("Invalid record payload")

        row_id = self._first_non_empty(
            record.get("RowID"),
            record.get("row_id"),
        )
        if not row_id:
            raise ValueError("Missing RowID")

        product_name = self._first_non_empty(
            record.get("ProductName"),
            record.get("product_name"),
            record.get("Name"),
            record.get("title"),
            record.get("name"),
        )
        category_id = self._first_non_empty(
            record.get("CategoryID"),
            record.get("category_id"),
            record.get("Category"),
            record.get("category"),
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
