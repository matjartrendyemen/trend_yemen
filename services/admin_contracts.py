from typing import Literal, TypedDict


EncodingState = Literal["complete", "partial", "unresolved"]


class SmartEncodingInputs(TypedDict):
    row_anchor: str
    sku_anchor: str
    category_anchor: str
    image_anchor: str
    status_anchor: str
    missing_fields: list[str]
    state: EncodingState


class AdminReadiness(TypedDict):
    has_row_id: bool
    has_sku: bool
    has_category: bool
    has_image_reference: bool
    processing_terminal: bool
    eligible_for_admin_identity: bool


class AdminProductRecord(TypedDict):
    row_id: str
    product_name: str
    sku: str
    category_id: str
    source_image_url: str
    final_image_url: str
    processing_status: str
    quality_status: str
    error_message: str
    smart_encoding_inputs: SmartEncodingInputs
    readiness: AdminReadiness
