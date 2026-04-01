# Smart Encoding logic layer (Slice 1)
# NOTE: This layer derives identity inputs ONLY from existing sheet data.
# It MUST NOT modify pipeline, storage, or external systems.

from typing import Dict, Any, List


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def build_smart_encoding_inputs(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build SmartEncodingInputs from raw sheet row (no side effects)."""

    row_anchor = _clean(row.get("RowID"))
    sku_anchor = _clean(row.get("SKU"))
    category_anchor = _clean(row.get("CategoryID"))

    final_image = _clean(row.get("FinalImageURL"))
    source_image = _clean(row.get("ImageURL"))
    image_anchor = final_image or source_image

    processing = _clean(row.get("ProcessingStatus"))
    quality = _clean(row.get("QualityStatus"))
    status_anchor = f"{processing}+{quality}" if quality else processing

    missing: List[str] = []

    if not row_anchor:
        missing.append("row_anchor")
    if not sku_anchor:
        missing.append("sku_anchor")
    if not category_anchor:
        missing.append("category_anchor")
    if not image_anchor:
        missing.append("image_anchor")
    if not status_anchor:
        missing.append("status_anchor")

    if not missing:
        state = "complete"
    elif row_anchor and (sku_anchor or image_anchor or status_anchor):
        state = "partial"
    else:
        state = "unresolved"

    return {
        "row_anchor": row_anchor,
        "sku_anchor": sku_anchor,
        "category_anchor": category_anchor,
        "image_anchor": image_anchor,
        "status_anchor": status_anchor,
        "missing_fields": missing,
        "state": state,
    }


def classify_readiness(inputs: Dict[str, Any], row: Dict[str, Any]) -> str:
    """Return admin-level readiness classification."""

    state = inputs["state"]
    processing = _clean(row.get("ProcessingStatus"))
    quality = _clean(row.get("QualityStatus"))

    if state == "complete":
        return "ready"

    if state == "partial" or quality == "NeedsReview":
        return "needs_review"

    return "invalid"
