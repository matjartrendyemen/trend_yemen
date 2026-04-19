# services/media_matching_service.py

from datetime import datetime, timezone


class MediaMatchingService:
    ROLE_PRIORITY = {
        "original": 1,
        "video": 2,
        "additional": 3,
        "lifestyle": 4,
    }

    DEFAULT_SOURCE_TAG = "dummy_matcher"

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

    def _slugify(self, value):
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value))
        while "--" in safe:
            safe = safe.replace("--", "-")
        return safe.strip("-") or "item"

    def _build_candidate(
        self,
        *,
        source_tag,
        media_type,
        role,
        rank,
        score,
        label,
        url,
    ):
        normalized_role = self._normalize_role(role)
        normalized_type = self._normalize_type(media_type)

        return {
            "source_tag": self._clean_str(source_tag) or self.DEFAULT_SOURCE_TAG,
            "type": normalized_type,
            "role": normalized_role,
            "priority": self.ROLE_PRIORITY[normalized_role],
            "rank": int(rank),
            "score": self._normalize_score(score),
            "label": self._clean_str(label),
            "url": self._clean_str(url),
        }

    def _normalize_role(self, value):
        normalized = self._clean_str(value).lower()
        if normalized in self.ROLE_PRIORITY:
            return normalized
        return "additional"

    def _normalize_type(self, value):
        normalized = self._clean_str(value).lower()
        if normalized == "video":
            return "video"
        return "image"

    def _normalize_score(self, value):
        try:
            return round(float(value), 4)
        except Exception:
            return None

    def _sort_and_reindex_candidates(self, candidates):
        ordered = sorted(
            candidates,
            key=lambda item: (
                int(item.get("priority", 999)),
                int(item.get("rank", 999)),
                -(item.get("score") if isinstance(item.get("score"), (int, float)) else -1),
                item.get("label", ""),
            ),
        )

        reindexed = []
        for idx, candidate in enumerate(ordered, start=1):
            normalized = dict(candidate)
            normalized["rank"] = idx
            reindexed.append(normalized)

        return reindexed

    def _build_candidates(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)

        name_slug = self._slugify(name or "product")
        category_slug = self._slugify(category or "category")
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"

        candidates = [
            self._build_candidate(
                source_tag=self.DEFAULT_SOURCE_TAG,
                media_type="image",
                role="original",
                rank=1,
                score=0.98,
                label=f"{label_base} Original",
                url=f"dummy://media/{name_slug}-original.jpg",
            ),
            self._build_candidate(
                source_tag=self.DEFAULT_SOURCE_TAG,
                media_type="video",
                role="video",
                rank=2,
                score=0.93,
                label=f"{label_base} Video",
                url=f"dummy://media/{name_slug}-video.mp4",
            ),
            self._build_candidate(
                source_tag=self.DEFAULT_SOURCE_TAG,
                media_type="image",
                role="additional",
                rank=3,
                score=0.87,
                label=f"{label_base} Additional",
                url=f"dummy://media/{category_slug}-additional.jpg",
            ),
            self._build_candidate(
                source_tag=self.DEFAULT_SOURCE_TAG,
                media_type="image",
                role="lifestyle",
                rank=4,
                score=0.81,
                label=f"{label_base} Lifestyle",
                url=f"dummy://media/{name_slug}-lifestyle.jpg",
            ),
        ]

        return self._sort_and_reindex_candidates(candidates)

    def generate_candidates_for_row(self, row_id, product_name="", category_id=""):
        normalized_row_id = self._clean_str(row_id)
        if not normalized_row_id:
            raise ValueError("Missing RowID")

        normalized_product_name = self._clean_str(product_name)
        normalized_category_id = self._clean_str(category_id)

        candidates = self._build_candidates(
            normalized_product_name,
            normalized_category_id,
        )

        matched_status = "ready" if candidates else "empty"

        self.sheets.update_media_fields(
            normalized_row_id,
            {
                "MatchedMediaJSON": candidates,
                "MatchedMediaCount": len(candidates),
                "MatchedMediaStatus": matched_status,
                "MatchedAt": self._now_iso(),
            },
        )

        return {
            "row_id": normalized_row_id,
            "matched_count": len(candidates),
            "matched_status": matched_status,
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
