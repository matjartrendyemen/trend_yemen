from typing import Any, Dict, List

from services.smart_encoding import build_smart_encoding_inputs, classify_readiness
from storage.sheets_store import SheetsStore


class AdminReadService:
    """Read-only admin layer built on top of SheetsStore.

    This service must not modify pipeline behavior or write back to Sheets.
    """

    def __init__(self, sheets_store: SheetsStore | None = None):
        self.sheets = sheets_store or SheetsStore()

    def get_all_admin_records(self) -> List[Dict[str, Any]]:
        rows = self._fetch_rows()
        return [self._build_admin_record(row) for row in rows]

    def _fetch_rows(self) -> List[Dict[str, Any]]:
        return self.sheets.sheet.get_all_records()

    def _build_admin_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        base = self._build_base_record(row)
        smart_inputs = build_smart_encoding_inputs(row)
        readiness = self._build_readiness(row, smart_inputs)

        return {
            **base,
            "smart_encoding_inputs": smart_inputs,
            "readiness": readiness,
        }

    def _build_base_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "row_id": self._clean(row.get("RowID")),
            "product_name": self._clean(row.get("ProductName")),
            "sku": self._clean(row.get("SKU")),
            "category_id": self._clean(row.get("CategoryID")),
            "source_image_url": self._clean(row.get("ImageURL")),
            "final_image_url": self._clean(row.get("FinalImageURL")),
            "processing_status": self._clean(row.get("ProcessingStatus")),
            "quality_status": self._clean(row.get("QualityStatus")),
            "error_message": self._clean(row.get("ErrorMessage")),
        }

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

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value).strip() if value is not None else ""
