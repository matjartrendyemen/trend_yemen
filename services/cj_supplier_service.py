import os
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests


class CJSupplierService:
    """
    Slice 1 + Slice 2 + Slice 3:
    - CJ auth via apiKey -> accessToken
    - on-demand raw retrieval only
    - raw images / video refs / basic metadata
    - no pricing usage
    - no ordering
    - no sync loops
    - safe matching engine
    - strict safe threshold
    - canonical candidate payload mapping for media layer
    """

    AUTH_URL = "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken"
    PRODUCT_LIST_V2_URL = "https://developers.cjdropshipping.com/api2.0/v1/product/listV2"
    PRODUCT_QUERY_URL = "https://developers.cjdropshipping.com/api2.0/v1/product/query"

    DEFAULT_TIMEOUT_SECONDS = 15
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    MAX_SEARCH_KEYWORDS = 2
    MAX_RAW_RESULTS_PER_QUERY = 8
    SAFE_MATCH_THRESHOLD = 0.62
    STRONG_MATCH_THRESHOLD = 0.78

    MATCH_STOPWORDS = {
        "the", "with", "for", "and", "new", "hot", "sale", "gift", "best",
        "product", "products", "item", "items", "tool", "tools", "set",
        "piece", "pieces", "pack", "kit", "portable", "smart", "wireless",
        "usb", "led", "mini", "pro", "max", "plus",
        "من", "في", "على", "الى", "إلى", "مع", "عن", "هذا", "هذه", "ذلك",
        "تلك", "منتج", "أداة", "اداة", "قطعة", "قطع", "جديد", "عرض", "عدة",
        "طقم", "لل", "لـ", "مناسب", "عملية", "عملي",
    }

    def __init__(self):
        self.api_key = (os.getenv("CJ_API_KEY") or "").strip()
        self.timeout_seconds = self.DEFAULT_TIMEOUT_SECONDS

        self._access_token: str = ""
        self._access_token_expires_at: Optional[datetime] = None
        self._last_error: str = ""

    def get_last_error(self) -> str:
        return self._last_error

    def _set_error(self, message: str) -> None:
        self._last_error = (message or "").strip()

    def _clear_error(self) -> None:
        self._last_error = ""

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def _clean_str(self, value: Any) -> str:
        return str(value or "").strip()

    def _safe_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _is_token_valid(self) -> bool:
        if not self._access_token:
            return False

        if not self._access_token_expires_at:
            return True

        return self._utcnow() < (self._access_token_expires_at - timedelta(minutes=5))

    def _parse_expiry(self, value: Any) -> Optional[datetime]:
        text = self._clean_str(value)
        if not text:
            return None

        normalized = text.replace("Z", "+00:00")

        try:
            dt = datetime.fromisoformat(normalized)
        except Exception:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    def _extract_data_object(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                return data
        return {}

    def _request(
        self,
        *,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                params=params or {},
                json=json_body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as e:
            self._set_error(f"CJ request failed: {e}")
            return None

        if response.status_code != 200:
            self._set_error(
                f"CJ request failed with HTTP {response.status_code}: {response.text[:300]}"
            )
            return None

        try:
            payload = response.json()
        except ValueError:
            self._set_error("CJ response is not valid JSON")
            return None

        if not isinstance(payload, dict):
            self._set_error("CJ response payload is not an object")
            return None

        success = payload.get("success")
        result = payload.get("result")
        code = payload.get("code")
        message = self._clean_str(payload.get("message"))

        if success is False or result is False:
            self._set_error(
                f"CJ API returned failure (code={code}, message={message or 'unknown'})"
            )
            return None

        self._clear_error()
        return payload

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        if not force_refresh and self._is_token_valid():
            return self._access_token

        if not self.api_key:
            self._set_error("CJ_API_KEY is missing")
            return None

        payload = self._request(
            method="POST",
            url=self.AUTH_URL,
            headers={"Content-Type": "application/json"},
            json_body={"apiKey": self.api_key},
        )
        if not payload:
            return None

        data = self._extract_data_object(payload)
        access_token = self._clean_str(data.get("accessToken"))
        expiry = self._parse_expiry(data.get("accessTokenExpiryDate"))

        if not access_token:
            self._set_error("CJ access token missing in auth response")
            return None

        self._access_token = access_token
        self._access_token_expires_at = expiry
        self._clear_error()
        return self._access_token

    def _build_auth_headers(self) -> Optional[Dict[str, str]]:
        access_token = self.get_access_token()
        if not access_token:
            return None

        return {
            "Content-Type": "application/json",
            "CJ-Access-Token": access_token,
        }

    def search_products_raw(
        self,
        keyword: str,
        page: int = 1,
        size: int = DEFAULT_PAGE_SIZE,
        include_video: bool = True,
        include_category: bool = True,
    ) -> List[Dict[str, Any]]:
        cleaned_keyword = self._clean_str(keyword)
        if not cleaned_keyword:
            self._set_error("CJ keyword is required")
            return []

        headers = self._build_auth_headers()
        if not headers:
            return []

        page_value = max(1, self._safe_int(page, 1))
        size_value = self._safe_int(size, self.DEFAULT_PAGE_SIZE)
        size_value = max(1, min(size_value, self.MAX_PAGE_SIZE))

        features: List[str] = []
        if include_category:
            features.append("enable_category")
        if include_video:
            features.append("enable_video")

        payload = self._request(
            method="GET",
            url=self.PRODUCT_LIST_V2_URL,
            headers=headers,
            params={
                "keyWord": cleaned_keyword,
                "page": page_value,
                "size": size_value,
                "orderBy": 0,
                "sort": "desc",
                "features": features,
            },
        )
        if not payload:
            return []

        data = self._extract_data_object(payload)
        content = data.get("content")

        flattened_products: List[Dict[str, Any]] = []

        if isinstance(content, list):
            for bucket in content:
                if not isinstance(bucket, dict):
                    continue

                product_list = bucket.get("productList")
                if isinstance(product_list, list):
                    for product in product_list:
                        if isinstance(product, dict):
                            flattened_products.append(product)

        if not flattened_products:
            direct_list = data.get("list")
            if isinstance(direct_list, list):
                for product in direct_list:
                    if isinstance(product, dict):
                        flattened_products.append(product)

        self._clear_error()
        return flattened_products

    def get_product_details_raw(
        self,
        *,
        pid: str = "",
        product_sku: str = "",
        variant_sku: str = "",
        include_video: bool = True,
    ) -> Optional[Dict[str, Any]]:
        pid = self._clean_str(pid)
        product_sku = self._clean_str(product_sku)
        variant_sku = self._clean_str(variant_sku)

        if not pid and not product_sku and not variant_sku:
            self._set_error("CJ detail query requires pid or product_sku or variant_sku")
            return None

        headers = self._build_auth_headers()
        if not headers:
            return None

        params: Dict[str, Any] = {}
        if pid:
            params["pid"] = pid
        elif product_sku:
            params["productSku"] = product_sku
        else:
            params["variantSku"] = variant_sku

        if include_video:
            params["features"] = ["enable_video"]

        payload = self._request(
            method="GET",
            url=self.PRODUCT_QUERY_URL,
            headers=headers,
            params=params,
        )
        if not payload:
            return None

        data = self._extract_data_object(payload)

        if isinstance(data.get("content"), list) and data["content"]:
            first_item = data["content"][0]
            if isinstance(first_item, dict):
                return first_item

        if isinstance(data.get("list"), list) and data["list"]:
            first_item = data["list"][0]
            if isinstance(first_item, dict):
                return first_item

        if data:
            return data

        self._set_error("CJ detail response did not include usable data")
        return None

    def _collect_possible_image_urls(self, *objects: Any) -> List[str]:
        keys = [
            "bigImage",
            "productImage",
            "image",
            "mainImage",
            "mainImageUrl",
            "imageUrl",
        ]
        list_keys = [
            "imageList",
            "images",
            "productImageList",
            "extraImageList",
            "productImages",
            "galleryImages",
        ]

        urls: List[str] = []
        seen = set()

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            for key in keys:
                value = obj.get(key)
                url = self._clean_str(value)
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

            for key in list_keys:
                value = obj.get(key)

                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            url = self._clean_str(item)
                            if url and url not in seen:
                                seen.add(url)
                                urls.append(url)
                        elif isinstance(item, dict):
                            for nested_key in ["url", "image", "imageUrl", "src"]:
                                url = self._clean_str(item.get(nested_key))
                                if url and url not in seen:
                                    seen.add(url)
                                    urls.append(url)

        return urls

    def _collect_possible_video_refs(self, *objects: Any) -> List[str]:
        keys = [
            "video",
            "videoUrl",
        ]
        list_keys = [
            "videoList",
            "productVideo",
            "videos",
            "videoUrls",
        ]

        refs: List[str] = []
        seen = set()

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            for key in keys:
                value = self._clean_str(obj.get(key))
                if value and value not in seen:
                    seen.add(value)
                    refs.append(value)

            for key in list_keys:
                value = obj.get(key)

                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            ref = self._clean_str(item)
                            if ref and ref not in seen:
                                seen.add(ref)
                                refs.append(ref)
                        elif isinstance(item, dict):
                            for nested_key in ["url", "videoUrl", "src", "id", "value"]:
                                ref = self._clean_str(item.get(nested_key))
                                if ref and ref not in seen:
                                    seen.add(ref)
                                    refs.append(ref)

        return refs

    def _build_raw_record(
        self,
        product: Dict[str, Any],
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        detail = detail or {}

        image_urls = self._collect_possible_image_urls(product, detail)
        video_refs = self._collect_possible_video_refs(product, detail)

        product_id = self._clean_str(
            product.get("id")
            or product.get("productId")
            or detail.get("id")
            or detail.get("productId")
            or detail.get("pid")
        )
        product_name = self._clean_str(
            product.get("nameEn")
            or product.get("productNameEn")
            or detail.get("nameEn")
            or detail.get("productNameEn")
            or product.get("productName")
            or detail.get("productName")
        )
        product_sku = self._clean_str(
            product.get("sku")
            or product.get("spu")
            or product.get("productSku")
            or detail.get("sku")
            or detail.get("spu")
            or detail.get("productSku")
        )
        category_name = self._clean_str(
            product.get("threeCategoryName")
            or product.get("categoryName")
            or detail.get("threeCategoryName")
            or detail.get("categoryName")
            or product.get("twoCategoryName")
            or detail.get("twoCategoryName")
            or product.get("oneCategoryName")
            or detail.get("oneCategoryName")
        )

        has_video = bool(video_refs) or str(product.get("isVideo") or detail.get("isVideo") or "") == "1"

        return {
            "source_family": "supplier",
            "source_name": "cj",
            "source_tag": "cj_supplier_raw",
            "product_id": product_id,
            "product_name": product_name,
            "product_sku": product_sku,
            "supplier_name": self._clean_str(product.get("supplierName") or detail.get("supplierName")),
            "supplier_id": self._clean_str(product.get("supplierId") or detail.get("supplierId")),
            "category_name": category_name,
            "product_type": self._clean_str(product.get("productType") or detail.get("productType")),
            "sale_status": self._clean_str(product.get("saleStatus") or detail.get("saleStatus") or detail.get("status")),
            "main_image_url": image_urls[0] if image_urls else "",
            "image_urls": image_urls,
            "has_video": has_video,
            "video_refs": video_refs,
            "video_urls": [ref for ref in video_refs if ref.startswith("http://") or ref.startswith("https://")],
            "basic_metadata": {
                "listed_num": product.get("listedNum", detail.get("listedNum")),
                "authority_status": product.get("authorityStatus", detail.get("authorityStatus")),
                "is_video": product.get("isVideo", detail.get("isVideo")),
                "create_time": product.get("createTime", detail.get("createTime") or detail.get("createrTime")),
                "remark": product.get("remark", detail.get("remark")),
            },
            "raw_product": product,
            "raw_detail": detail,
        }

    def collect_raw_media_records(
        self,
        keyword: str,
        page: int = 1,
        size: int = DEFAULT_PAGE_SIZE,
        hydrate_details: bool = True,
        include_video: bool = True,
    ) -> List[Dict[str, Any]]:
        products = self.search_products_raw(
            keyword=keyword,
            page=page,
            size=size,
            include_video=include_video,
            include_category=True,
        )
        if not products:
            return []

        records: List[Dict[str, Any]] = []

        for product in products:
            if not isinstance(product, dict):
                continue

            detail: Optional[Dict[str, Any]] = None

            if hydrate_details:
                pid = self._clean_str(product.get("id") or product.get("productId"))
                sku = self._clean_str(product.get("sku") or product.get("spu") or product.get("productSku"))

                detail = self.get_product_details_raw(
                    pid=pid,
                    product_sku="" if pid else sku,
                    include_video=include_video,
                )

            records.append(self._build_raw_record(product=product, detail=detail))

        return records

    # ---------------------------------------------------------------------
    # Slice 2 — Safe matching engine
    # ---------------------------------------------------------------------

    def _normalize_match_text(self, value: Any) -> str:
        text = self._clean_str(value).lower()
        text = re.sub(r"[_|/\\-]+", " ", text)
        text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize_for_match(self, value: Any) -> List[str]:
        normalized = self._normalize_match_text(value)
        if not normalized:
            return []

        tokens = normalized.split()
        filtered: List[str] = []

        for token in tokens:
            if token in self.MATCH_STOPWORDS:
                continue
            if len(token) < 2:
                continue
            filtered.append(token)

        return filtered

    def _build_safe_search_keywords(self, product_name: str, category_id: str = "") -> List[str]:
        name_tokens = self._tokenize_for_match(product_name)
        category_tokens = self._tokenize_for_match(category_id)

        keywords: List[str] = []

        primary = " ".join(name_tokens[:5]).strip()
        if primary:
            keywords.append(primary)

        combined_tokens = name_tokens[:4]
        if category_tokens:
            combined_tokens += category_tokens[:2]

        combined = " ".join(combined_tokens).strip()
        if combined and combined not in keywords:
            keywords.append(combined)

        return keywords[: self.MAX_SEARCH_KEYWORDS]

    def _sequence_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return round(SequenceMatcher(None, a, b).ratio(), 4)

    def _token_overlap_ratio(self, source_tokens: List[str], target_tokens: List[str]) -> float:
        if not source_tokens or not target_tokens:
            return 0.0

        source_set = set(source_tokens)
        target_set = set(target_tokens)
        overlap = source_set.intersection(target_set)

        if not overlap:
            return 0.0

        return round(len(overlap) / max(len(source_set), 1), 4)

    def _category_overlap_ratio(self, category_tokens: List[str], candidate_tokens: List[str]) -> float:
        if not category_tokens or not candidate_tokens:
            return 0.0

        category_set = set(category_tokens)
        candidate_set = set(candidate_tokens)
        overlap = category_set.intersection(candidate_set)

        if not overlap:
            return 0.0

        return round(len(overlap) / max(len(category_set), 1), 4)

    def _candidate_name_fields(self, raw_record: Dict[str, Any]) -> str:
        return self._clean_str(
            raw_record.get("product_name")
            or raw_record.get("product_sku")
            or raw_record.get("category_name")
        )

    def _score_raw_record(
        self,
        *,
        product_name: str,
        category_id: str,
        matched_keyword: str,
        raw_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        query_name = self._normalize_match_text(product_name)
        query_tokens = self._tokenize_for_match(product_name)
        category_tokens = self._tokenize_for_match(category_id)
        keyword_tokens = self._tokenize_for_match(matched_keyword)

        candidate_name = self._normalize_match_text(self._candidate_name_fields(raw_record))
        candidate_category = self._normalize_match_text(raw_record.get("category_name"))

        candidate_tokens = self._tokenize_for_match(
            f"{candidate_name} {candidate_category}"
        )

        name_similarity = self._sequence_similarity(query_name, candidate_name)
        keyword_similarity = self._sequence_similarity(
            self._normalize_match_text(matched_keyword),
            candidate_name,
        )
        token_overlap = self._token_overlap_ratio(query_tokens, candidate_tokens)
        keyword_overlap = self._token_overlap_ratio(keyword_tokens, candidate_tokens)
        category_overlap = self._category_overlap_ratio(category_tokens, candidate_tokens)

        exact_name_bonus = 0.10 if query_name and query_name == candidate_name else 0.0
        main_image_bonus = 0.05 if self._clean_str(raw_record.get("main_image_url")) else 0.0
        video_bonus = 0.02 if raw_record.get("has_video") else 0.0

        confidence = (
            (name_similarity * 0.42)
            + (keyword_similarity * 0.18)
            + (token_overlap * 0.25)
            + (keyword_overlap * 0.10)
            + (category_overlap * 0.08)
            + exact_name_bonus
            + main_image_bonus
            + video_bonus
        )

        confidence = round(min(confidence, 1.0), 4)

        return {
            "confidence": confidence,
            "metrics": {
                "name_similarity": name_similarity,
                "keyword_similarity": keyword_similarity,
                "token_overlap": token_overlap,
                "keyword_overlap": keyword_overlap,
                "category_overlap": category_overlap,
                "exact_name_bonus": exact_name_bonus,
                "main_image_bonus": main_image_bonus,
                "video_bonus": video_bonus,
            },
        }

    def _is_safe_match(
        self,
        *,
        score_payload: Dict[str, Any],
    ) -> bool:
        confidence = float(score_payload.get("confidence", 0.0))
        metrics = score_payload.get("metrics") or {}

        name_similarity = float(metrics.get("name_similarity", 0.0))
        token_overlap = float(metrics.get("token_overlap", 0.0))
        keyword_overlap = float(metrics.get("keyword_overlap", 0.0))

        if confidence < self.SAFE_MATCH_THRESHOLD:
            return False

        if name_similarity >= 0.90:
            return True

        if token_overlap >= 0.50 and keyword_overlap >= 0.50:
            return True

        if name_similarity >= 0.72 and token_overlap >= 0.34:
            return True

        if confidence >= self.STRONG_MATCH_THRESHOLD:
            return True

        return False

    def _dedupe_ranked_matches(self, ranked_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen = set()

        for item in ranked_matches:
            record = item.get("raw_record") or {}
            dedupe_key = (
                self._clean_str(record.get("product_id")),
                self._clean_str(record.get("main_image_url")),
                self._clean_str(record.get("product_name")),
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            deduped.append(item)

        return deduped

    def find_safe_matches(
        self,
        *,
        product_name: str,
        category_id: str = "",
        max_results: int = 3,
        hydrate_details: bool = True,
        include_video: bool = True,
    ) -> List[Dict[str, Any]]:
        cleaned_product_name = self._clean_str(product_name)
        if not cleaned_product_name:
            self._set_error("Safe CJ matching requires product_name")
            return []

        search_keywords = self._build_safe_search_keywords(
            product_name=cleaned_product_name,
            category_id=category_id,
        )
        if not search_keywords:
            self._set_error("Safe CJ matching could not derive usable search keywords")
            return []

        ranked_matches: List[Dict[str, Any]] = []

        for keyword in search_keywords:
            raw_records = self.collect_raw_media_records(
                keyword=keyword,
                page=1,
                size=self.MAX_RAW_RESULTS_PER_QUERY,
                hydrate_details=hydrate_details,
                include_video=include_video,
            )

            if not raw_records:
                continue

            for raw_record in raw_records:
                if not isinstance(raw_record, dict):
                    continue

                score_payload = self._score_raw_record(
                    product_name=cleaned_product_name,
                    category_id=category_id,
                    matched_keyword=keyword,
                    raw_record=raw_record,
                )

                if not self._is_safe_match(score_payload=score_payload):
                    continue

                ranked_matches.append({
                    "matched_keyword": keyword,
                    "match_confidence": score_payload["confidence"],
                    "match_metrics": score_payload["metrics"],
                    "raw_record": raw_record,
                })

        if not ranked_matches:
            self._clear_error()
            return []

        ranked_matches.sort(
            key=lambda item: (
                -float(item.get("match_confidence", 0.0)),
                -float((item.get("match_metrics") or {}).get("name_similarity", 0.0)),
                -float((item.get("match_metrics") or {}).get("token_overlap", 0.0)),
            )
        )

        ranked_matches = self._dedupe_ranked_matches(ranked_matches)

        safe_results: List[Dict[str, Any]] = []
        for item in ranked_matches[: max(1, int(max_results))]:
            raw_record = dict(item["raw_record"])
            raw_record["source_family"] = "supplier"
            raw_record["source_name"] = "cj"
            raw_record["source_tag"] = "cj_supplier"
            raw_record["match_confidence"] = item["match_confidence"]
            raw_record["matched_keyword"] = item["matched_keyword"]
            raw_record["match_metrics"] = item["match_metrics"]
            safe_results.append(raw_record)

        self._clear_error()
        return safe_results

    def find_best_safe_match(
        self,
        *,
        product_name: str,
        category_id: str = "",
        hydrate_details: bool = True,
        include_video: bool = True,
    ) -> Optional[Dict[str, Any]]:
        safe_matches = self.find_safe_matches(
            product_name=product_name,
            category_id=category_id,
            max_results=1,
            hydrate_details=hydrate_details,
            include_video=include_video,
        )
        if not safe_matches:
            return None
        return safe_matches[0]

    # ---------------------------------------------------------------------
    # Slice 3 — Canonical candidate mapping
    # ---------------------------------------------------------------------

    def _dedupe_urls(self, values: List[str]) -> List[str]:
        urls: List[str] = []
        seen = set()

        for value in values:
            url = self._clean_str(value)
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)

        return urls

    def build_canonical_candidate_payloads(
        self,
        safe_match: Dict[str, Any],
        *,
        base_label: str = "",
        max_images: int = 2,
        include_video: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Returns canonical-ish payloads ready to be normalized by MediaMatchingService.
        No schema redesign:
        - source_family = supplier
        - source_name = cj
        - source_tag = cj_supplier
        """
        if not isinstance(safe_match, dict):
            return []

        product_name = self._clean_str(
            safe_match.get("product_name")
            or safe_match.get("product_sku")
            or base_label
            or "CJ Match"
        )
        label_base = self._clean_str(base_label) or product_name or "CJ Match"

        confidence = max(0.0, min(self._safe_float(safe_match.get("match_confidence"), 0.0), 0.99))
        product_id = self._clean_str(safe_match.get("product_id"))
        product_sku = self._clean_str(safe_match.get("product_sku"))
        matched_keyword = self._clean_str(safe_match.get("matched_keyword"))

        image_urls = self._dedupe_urls(
            [safe_match.get("main_image_url", "")]
            + list(safe_match.get("image_urls") or [])
        )
        video_urls = self._dedupe_urls(list(safe_match.get("video_urls") or []))

        payloads: List[Dict[str, Any]] = []

        if include_video and video_urls:
            payloads.append({
                "source_family": "supplier",
                "source_name": "cj",
                "source_tag": "cj_supplier",
                "type": "video",
                "role": "video",
                "rank": 20,
                "score": round(min(confidence + 0.02, 0.99), 4),
                "label": f"{label_base} — CJ Video",
                "url": video_urls[0],
                "supplier_product_id": product_id,
                "supplier_product_sku": product_sku,
                "matched_keyword": matched_keyword,
                "match_confidence": confidence,
                "match_metrics": safe_match.get("match_metrics") or {},
            })

        for idx, image_url in enumerate(image_urls[: max(0, int(max_images))], start=1):
            payloads.append({
                "source_family": "supplier",
                "source_name": "cj",
                "source_tag": "cj_supplier",
                "type": "image",
                "role": "additional",
                "rank": 30 + idx,
                "score": round(max(confidence - ((idx - 1) * 0.01), 0.0), 4),
                "label": f"{label_base} — CJ Image {idx}",
                "url": image_url,
                "supplier_product_id": product_id,
                "supplier_product_sku": product_sku,
                "matched_keyword": matched_keyword,
                "match_confidence": confidence,
                "match_metrics": safe_match.get("match_metrics") or {},
            })

        return payloads
