# services/media_matching_service.py

from datetime import datetime, timezone

from adapters.pexels_adapter import PexelsAdapter


class MediaMatchingService:
    ROLE_PRIORITY = {
        "original": 1,
        "video": 2,
        "additional": 3,
        "lifestyle": 4,
    }

    DEFAULT_SOURCE_TAG = "dummy_matcher"
    SEED_SOURCE_TAG = "seed_media"
    PEXELS_SOURCE_TAG = "pexels"

    def __init__(self, sheets_store):
        self.sheets = sheets_store
        self.pexels = PexelsAdapter()

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

    def _is_searchable_keyword(self, value):
        text = self._clean_str(value)
        if not text:
            return False

        if len(text) < 2:
            return False

        return any(ch.isalpha() for ch in text)

    def _build_lifestyle_keywords(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)

        keyword_candidates = [
            name,
            f"{name} {category}".strip() if name and category else "",
            category,
        ]

        seen = set()
        keywords = []

        for keyword in keyword_candidates:
            cleaned = self._clean_str(keyword)
            lowered = cleaned.lower()

            if not self._is_searchable_keyword(cleaned):
                continue

            if lowered in seen:
                continue

            seen.add(lowered)
            keywords.append(cleaned)

        return keywords

    def _build_seed_original_candidate(self, product_name, category_id, seed_media_url):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"

        cleaned_seed_url = self._clean_str(seed_media_url)
        if cleaned_seed_url:
            return self._build_candidate(
                source_tag=self.SEED_SOURCE_TAG,
                media_type="image",
                role="original",
                rank=1,
                score=1.0,
                label=f"{label_base} Original",
                url=cleaned_seed_url,
            )

        name_slug = self._slugify(name or "product")
        return self._build_candidate(
            source_tag=self.DEFAULT_SOURCE_TAG,
            media_type="image",
            role="original",
            rank=1,
            score=0.98,
            label=f"{label_base} Original",
            url=f"dummy://media/{name_slug}-original.jpg",
        )

    def _build_video_candidate(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"
        name_slug = self._slugify(name or "product")

        return self._build_candidate(
            source_tag=self.DEFAULT_SOURCE_TAG,
            media_type="video",
            role="video",
            rank=2,
            score=0.93,
            label=f"{label_base} Video",
            url=f"dummy://media/{name_slug}-video.mp4",
        )

    def _build_additional_candidate(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"
        category_slug = self._slugify(category or "category")

        return self._build_candidate(
            source_tag=self.DEFAULT_SOURCE_TAG,
            media_type="image",
            role="additional",
            rank=3,
            score=0.87,
            label=f"{label_base} Additional",
            url=f"dummy://media/{category_slug}-additional.jpg",
        )

    def _build_dummy_lifestyle_candidate(self, product_name, category_id):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"
        name_slug = self._slugify(name or "product")

        return self._build_candidate(
            source_tag=self.DEFAULT_SOURCE_TAG,
            media_type="image",
            role="lifestyle",
            rank=4,
            score=0.75,
            label=f"{label_base} Lifestyle",
            url=f"dummy://media/{name_slug}-lifestyle.jpg",
        )

    def _fetch_pexels_lifestyle_results(self, product_name, category_id, count=3):
        keywords = self._build_lifestyle_keywords(product_name, category_id)
        if not keywords:
            return []

        results = []
        seen_urls = set()

        for keyword in keywords:
            try:
                urls = self.pexels.fetch_lifestyle_images(keyword=keyword, count=count) or []
            except Exception:
                urls = []

            for url in urls:
                cleaned_url = self._clean_str(url)
                if not cleaned_url or cleaned_url in seen_urls:
                    continue

                seen_urls.add(cleaned_url)
                results.append({
                    "keyword": keyword,
                    "url": cleaned_url,
                })

                if len(results) >= count:
                    return results

        return results

    def _build_pexels_lifestyle_candidates(self, product_name, category_id, count=3):
        name = self._clean_str(product_name)
        category = self._clean_str(category_id)
        label_base = " - ".join([part for part in [name, category] if part]) or "Generic Product"

        pexels_results = self._fetch_pexels_lifestyle_results(
            product_name=product_name,
            category_id=category_id,
            count=count,
        )

        candidates = []
        for index, item in enumerate(pexels_results, start=1):
            score = round(0.79 - ((index - 1) * 0.01), 4)
            candidates.append(
                self._build_candidate(
                    source_tag=self.PEXELS_SOURCE_TAG,
                    media_type="image",
                    role="lifestyle",
                    rank=4 + index,
                    score=score,
                    label=f"{label_base} Lifestyle {index}",
                    url=item["url"],
                )
            )

        return candidates

    def _build_candidates(self, product_name, category_id, seed_media_url=""):
        candidates = [
            self._build_seed_original_candidate(
                product_name=product_name,
                category_id=category_id,
                seed_media_url=seed_media_url,
            ),
            self._build_video_candidate(
                product_name=product_name,
                category_id=category_id,
            ),
            self._build_additional_candidate(
                product_name=product_name,
                category_id=category_id,
            ),
        ]

        pexels_lifestyle_candidates = self._build_pexels_lifestyle_candidates(
            product_name=product_name,
            category_id=category_id,
            count=3,
        )

        if pexels_lifestyle_candidates:
            candidates.extend(pexels_lifestyle_candidates)
        else:
            candidates.append(
                self._build_dummy_lifestyle_candidate(
                    product_name=product_name,
                    category_id=category_id,
                )
            )

        return self._sort_and_reindex_candidates(candidates)

    def generate_candidates_for_row(self, row_id, product_name="", category_id="", seed_media_url=""):
        normalized_row_id = self._clean_str(row_id)
        if not normalized_row_id:
            raise ValueError("Missing RowID")

        normalized_product_name = self._clean_str(product_name)
        normalized_category_id = self._clean_str(category_id)
        normalized_seed_media_url = self._clean_str(seed_media_url)

        candidates = self._build_candidates(
            normalized_product_name,
            normalized_category_id,
            normalized_seed_media_url,
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
        seed_media_url = self._first_non_empty(
            record.get("SeedMediaURL"),
            record.get("seed_media_url"),
            record.get("ImageURL"),
            record.get("source_image_url"),
            record.get("image_url"),
        )

        return self.generate_candidates_for_row(
            row_id=row_id,
            product_name=product_name,
            category_id=category_id,
            seed_media_url=seed_media_url,
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
