from datetime import datetime, timezone
from typing import Any, Dict, List

from services.smart_encoding import build_smart_encoding_inputs, classify_readiness
from storage.sheets_store import SheetsStore


class AdminReadService:
    """Read-only admin layer built on top of SheetsStore.

    This service must not modify pipeline behavior or write back to Sheets.
    """

    STUCK_PROCESSING_THRESHOLD_SECONDS = 15 * 60

    def __init__(self, sheets_store: SheetsStore | None = None):
        self.sheets = sheets_store or SheetsStore()

    def get_all_admin_records(self) -> List[Dict[str, Any]]:
        rows = self._fetch_rows()
        return [self._build_admin_record(row) for row in rows]

    def _fetch_rows(self) -> List[Dict[str, Any]]:
        return self.sheets.sheet.get_all_records()

    def _build_admin_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        base = self._build_base_record(row)
        failure_visibility = self._build_failure_visibility(base)
        stuck_visibility = self._build_stuck_processing_visibility(row, base)
        smart_inputs = build_smart_encoding_inputs(row)
        readiness = self._build_readiness(row, smart_inputs)
        action_eligibility = self._build_action_eligibility(
            row=row,
            base_record=base,
            failure_visibility=failure_visibility,
            stuck_visibility=stuck_visibility,
        )

        return {
            **base,
            **failure_visibility,
            **stuck_visibility,
            "action_eligibility": action_eligibility,
            "smart_encoding_inputs": smart_inputs,
            "readiness": readiness,
        }

    def _build_base_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        source_image_url = self._clean(row.get("ImageURL"))
        processing_status = self._clean(row.get("ProcessingStatus"))
        price = self._clean(row.get("Price"))
        quality_status = self._clean(row.get("QualityStatus"))
        error_message = self._clean(row.get("ErrorMessage"))

        created_at = self._first_non_empty(
            row.get("CreatedAt"),
            row.get("created_at"),
            row.get("Timestamp"),
            row.get("timestamp"),
        )
        updated_at = self._first_non_empty(
            row.get("UpdatedAt"),
            row.get("updated_at"),
        )
        last_updated = self._first_non_empty(
            row.get("LastUpdated"),
            row.get("last_updated"),
            updated_at,
            created_at,
        )

        return {
            "row_id": self._clean(row.get("RowID")),
            "product_name": self._clean(row.get("ProductName")),
            "sku": self._clean(row.get("SKU")),
            "category_id": self._clean(row.get("CategoryID")),
            "source_image_url": source_image_url,
            "image_url": source_image_url,
            "final_image_url": self._clean(row.get("FinalImageURL")),
            "processing_status": processing_status,
            "status": processing_status,
            "price": price,
            "quality_status": quality_status,
            "error_message": error_message,
            "created_at": created_at,
            "updated_at": updated_at,
            "last_updated": last_updated,
        }

    def _build_failure_visibility(self, record: Dict[str, Any]) -> Dict[str, Any]:
        row_id = self._clean(record.get("row_id"))
        source_image_url = self._clean(record.get("source_image_url"))
        price = self._clean(record.get("price"))
        processing_status = self._clean(record.get("processing_status"))
        quality_status = self._clean(record.get("quality_status"))
        error_message = self._clean(record.get("error_message"))

        create_flow_status = (
            "succeeded" if row_id and source_image_url and price else "incomplete"
        )
        ingestion_status = (
            "succeeded" if row_id and source_image_url else "incomplete"
        )
        enrichment_status = self._build_enrichment_status(
            processing_status=processing_status,
            quality_status=quality_status,
            error_message=error_message,
        )

        failure_stage = ""
        failure_category = ""
        failure_summary = ""
        failure_class = ""
        retryability_status = "not_applicable"
        retryable = False
        retry_recommended = False
        retry_guidance = ""

        if enrichment_status == "failed":
            failure_stage = "downstream_enrichment"
            failure_category = self._classify_failure_category(error_message)
            failure_summary = self._build_failure_summary(failure_category)
            failure_class = self._build_failure_class(failure_category)
            retryability_status = self._build_retryability_status(failure_category)
            retryable = retryability_status == "retryable"
            retry_recommended = retryable
            retry_guidance = self._build_retry_guidance(failure_category)

        error_summary = self._build_error_summary(
            error_message=error_message,
            failure_category=failure_category,
            enrichment_status=enrichment_status,
        )

        operational_status = self._build_operational_status(
            processing_status=processing_status,
            enrichment_status=enrichment_status,
            retryability_status=retryability_status,
        )

        return {
            "create_flow_status": create_flow_status,
            "ingestion_status": ingestion_status,
            "enrichment_status": enrichment_status,
            "failure_stage": failure_stage,
            "failure_category": failure_category,
            "failure_class": failure_class,
            "failure_summary": failure_summary,
            "error_summary": error_summary,
            "retryability_status": retryability_status,
            "retryable": retryable,
            "retry_recommended": retry_recommended,
            "retry_guidance": retry_guidance,
            "operational_status": operational_status,
        }

    def _build_stuck_processing_visibility(
        self,
        row: Dict[str, Any],
        base_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        processing_status = self._clean(base_record.get("processing_status"))

        if processing_status != "Processing":
            return {
                "is_stuck_processing": False,
                "processing_age": "",
                "stuck_reason": "",
                "stuck_action_eligible": False,
            }

        reference_dt, reference_source = self._resolve_processing_reference_dt(row)

        if not reference_dt:
            return {
                "is_stuck_processing": False,
                "processing_age": "",
                "stuck_reason": "Processing timestamp metadata unavailable; row kept as non-stuck conservatively.",
                "stuck_action_eligible": False,
            }

        age_seconds = max(
            0,
            int((datetime.now(timezone.utc) - reference_dt).total_seconds()),
        )
        processing_age = self._format_duration(age_seconds)
        is_stuck_processing = age_seconds >= self.STUCK_PROCESSING_THRESHOLD_SECONDS

        if is_stuck_processing:
            stuck_reason = (
                f"Processing exceeded {self.STUCK_PROCESSING_THRESHOLD_SECONDS // 60}m threshold "
                f"based on {reference_source}."
            )
        else:
            stuck_reason = ""

        return {
            "is_stuck_processing": is_stuck_processing,
            "processing_age": processing_age,
            "stuck_reason": stuck_reason,
            "stuck_action_eligible": is_stuck_processing,
        }

    def _resolve_processing_reference_dt(self, row: Dict[str, Any]):
        candidates = [
            ("ProcessingStartedAt", row.get("ProcessingStartedAt")),
            ("UpdatedAt", row.get("UpdatedAt")),
            ("LastUpdated", row.get("LastUpdated")),
            ("CreatedAt", row.get("CreatedAt")),
            ("Timestamp", row.get("Timestamp")),
            ("processing_started_at", row.get("processing_started_at")),
            ("updated_at", row.get("updated_at")),
            ("last_updated", row.get("last_updated")),
            ("created_at", row.get("created_at")),
            ("timestamp", row.get("timestamp")),
        ]

        for source_name, raw_value in candidates:
            parsed = self._parse_datetime(raw_value)
            if parsed:
                return parsed, source_name

        return None, ""

    def _parse_datetime(self, value: Any):
        text = self._clean(value)
        if not text:
            return None

        normalized = text.replace("Z", "+00:00")

        try:
            dt = datetime.fromisoformat(normalized)
        except Exception:
            dt = None

        if dt is None:
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
            ]:
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except Exception:
                    continue

        if dt is None:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    def _format_duration(self, total_seconds: int) -> str:
        if total_seconds < 60:
            return f"{total_seconds}s"

        total_minutes, _ = divmod(total_seconds, 60)
        if total_minutes < 60:
            return f"{total_minutes}m"

        total_hours, minutes = divmod(total_minutes, 60)
        if total_hours < 24:
            return f"{total_hours}h {minutes}m"

        total_days, hours = divmod(total_hours, 24)
        return f"{total_days}d {hours}h"

    def _build_enrichment_status(
        self,
        processing_status: str,
        quality_status: str,
        error_message: str,
    ) -> str:
        processing = self._clean(processing_status)
        quality = self._clean(quality_status)
        error = self._clean(error_message)

        if processing == "Pending":
            return "pending"

        if processing == "Processing":
            return "processing"

        if processing == "Completed":
            return "completed"

        if processing == "Failed" or quality == "Failed" or error:
            return "failed"

        return "unknown"

    def _classify_failure_category(self, error_message: str) -> str:
        message = self._clean(error_message).lower()

        if not message:
            return ""

        if any(token in message for token in [
            "[rate_limit]",
            "429",
            "rate limit",
            "resource_exhausted",
            "quota",
            "too many requests",
        ]):
            return "rate_limit"

        if any(token in message for token in [
            "[service_unavailable]",
            "503",
            "service unavailable",
            "temporarily unavailable",
            "backend unavailable",
            "model is overloaded",
        ]):
            return "service_unavailable"

        return "general_failure"

    def _build_failure_class(self, failure_category: str) -> str:
        if failure_category == "rate_limit":
            return "downstream_rate_limit"

        if failure_category == "service_unavailable":
            return "downstream_service_unavailable"

        if failure_category == "general_failure":
            return "downstream_general_failure"

        return ""

    def _build_error_summary(
        self,
        error_message: str,
        failure_category: str,
        enrichment_status: str,
    ) -> str:
        if enrichment_status != "failed":
            return ""

        if failure_category == "rate_limit":
            return "Downstream enrichment failed بسبب Gemini rate limit (429)."

        if failure_category == "service_unavailable":
            return "Downstream enrichment failed بسبب Gemini service unavailable (503)."

        return self._truncate(self._clean(error_message), 160) or "Downstream enrichment failed."

    def _build_failure_summary(self, failure_category: str) -> str:
        if failure_category == "rate_limit":
            return "Create and registration succeeded, but downstream AI enrichment failed because Gemini hit rate limiting (429)."

        if failure_category == "service_unavailable":
            return "Create and registration succeeded, but downstream AI enrichment failed because Gemini was unavailable (503)."

        return "Create and registration succeeded, but downstream AI enrichment failed later."

    def _build_retryability_status(self, failure_category: str) -> str:
        if failure_category in {"rate_limit", "service_unavailable"}:
            return "retryable"

        return "not_clearly_retryable"

    def _build_retry_guidance(self, failure_category: str) -> str:
        if failure_category == "rate_limit":
            return "Retry is reasonable, but waiting briefly is recommended because this looks like a temporary rate limit."

        if failure_category == "service_unavailable":
            return "Retry is reasonable because this looks like a temporary provider outage."

        return "Retry may help, but this failure is not clearly classified as temporary."

    def _build_operational_status(
        self,
        processing_status: str,
        enrichment_status: str,
        retryability_status: str,
    ) -> str:
        processing = self._clean(processing_status)

        if enrichment_status == "failed" and retryability_status == "retryable":
            return "RetryableFailed"

        if processing:
            return processing

        return "Unknown"

    def _build_action_eligibility(
        self,
        row: Dict[str, Any],
        base_record: Dict[str, Any],
        failure_visibility: Dict[str, Any],
        stuck_visibility: Dict[str, Any],
    ) -> Dict[str, bool]:
        row_id = self._clean(base_record.get("row_id"))
        matched_media_status = self._clean(row.get("MatchedMediaStatus"))
        matched_media_count = self._safe_int(row.get("MatchedMediaCount"))
        stuck_action_allowed = bool(row_id) and bool(stuck_visibility.get("stuck_action_eligible"))

        return {
            "retry": bool(row_id) and failure_visibility.get("enrichment_status") == "failed",
            "match_media": bool(row_id),
            "select_final_media": (
                bool(row_id)
                and matched_media_status == "ready"
                and matched_media_count > 0
            ),
            "delete": bool(row_id),
            "reset_to_pending": stuck_action_allowed,
            "release_to_failed": stuck_action_allowed,
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            return 0

    def _build_readiness(self, row: Dict[str, Any], smart_inputs: Dict[str, Any]) -> Dict[str, Any]:
        processing_status = self._clean(row.get("ProcessingStatus"))
        source_image_url = self._clean(row.get("ImageURL"))
        final_image_url = self._clean(row.get("FinalImageURL"))
        readiness_status = classify_readiness(smart_inputs, row)

        return {
            "has_row_id": bool(self._clean(row.get("RowID"))),
            "has_sku": bool(self._clean(row.get("SKU"))),
            "has_category": bool(self._clean(row.get("CategoryID"))),
            "has_image_reference": bool(final_image_url or source_image_url),
            "processing_terminal": processing_status in {"Completed", "Failed"},
            "eligible_for_admin_identity": smart_inputs.get("state") != "unresolved",
            "status": readiness_status,
        }

    def _first_non_empty(self, *values: Any) -> str:
        for value in values:
            cleaned = self._clean(value)
            if cleaned:
                return cleaned
        return ""

    @staticmethod
    def _truncate(value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value).strip() if value is not None else ""
