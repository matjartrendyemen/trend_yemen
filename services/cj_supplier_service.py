import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests


class CJSupplierService:
    """
    Slice 1 only:
    - CJ auth via apiKey -> accessToken
    - on-demand raw retrieval only
    - raw images / video refs / basic metadata
    - no pricing usage
    - no ordering
    - no sync loops
    - failure-safe by returning empty results / None instead of breaking callers
    """

    AUTH_URL = "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken"
    PRODUCT_LIST_V2_URL = "https://developers.cjdropshipping.com/api2.0/v1/product/listV2"
    PRODUCT_QUERY_URL = "https://developers.cjdropshipping.com/api2.0/v1/product/query"

    DEFAULT_TIMEOUT_SECONDS = 15
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

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

    def _is_token_valid(self) -> bool:
        if not self._access_token:
            return False

        if not self._access_token_expires_at:
            return True

        # Refresh slightly before expiry to stay safe.
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
        """
        Raw product discovery via CJ product/listV2.
        Returns flattened product list only.
        """
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
            # Be tolerant in case CJ changes list shape.
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
        """
        Raw detail retrieval via CJ product/query.
        Only raw media/basic metadata usage.
        """
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

        # Tolerant extraction because CJ may return nested content/list/object.
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
        """
        On-demand raw retrieval for internal supplier foundation work.
        Returns raw-but-usable records.
        Failure-safe: returns [] instead of raising.
        """
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
