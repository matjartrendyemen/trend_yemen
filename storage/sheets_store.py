import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import gspread
from google.oauth2.service_account import Credentials


class SheetsStore:
    REQUIRED_RESULT_COLUMNS = [
        "ProductName",
        "SKU",
        "CategoryID",
        "FinalImageURL",
        "QualityStatus",
        "ErrorMessage",
    ]

    MEDIA_COLUMNS = [
        "SeedMediaType",
        "SeedMediaURL",
        "SeedMediaStatus",
        "MatchedMediaJSON",
        "MatchedMediaCount",
        "MatchedMediaStatus",
        "MatchedAt",
        "FinalPrimaryMediaType",
        "FinalPrimaryMediaURL",
        "FinalGalleryMediaJSON",
        "FinalMediaStatus",
        "FinalizedAt",
    ]

    MEDIA_JSON_COLUMNS = {
        "MatchedMediaJSON",
        "FinalGalleryMediaJSON",
    }

    REGISTRATION_REQUIRED_COLUMNS = [
        "RowID",
        "ProcessingStartedAt",
    ]

    def __init__(self):
        self.sheet_name = "Products"

        creds_raw = os.getenv("GOOGLE_CREDENTIALS")
        spreadsheet_id = os.getenv("SPREADSHEET_ID")

        if not creds_raw:
            raise ValueError("GOOGLE_CREDENTIALS is missing")
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID is missing")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials_info = json.loads(creds_raw)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes,
        )

        client = gspread.authorize(credentials)
        self.sheet = client.open_by_key(spreadsheet_id).worksheet(self.sheet_name)

        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

    def _refresh_headers(self):
        self.headers = self.sheet.row_values(1)
        self.col_map = {name: idx + 1 for idx, name in enumerate(self.headers)}

    def _ensure_required_columns(self):
        expected_columns = (
            self.REQUIRED_RESULT_COLUMNS
            + self.MEDIA_COLUMNS
            + self.REGISTRATION_REQUIRED_COLUMNS
        )
        missing_columns = [
            col for col in expected_columns if col not in self.col_map
        ]

        if not missing_columns:
            return

        next_col_index = len(self.headers) + 1

        for column_name in missing_columns:
            self.sheet.update_cell(1, next_col_index, column_name)
            next_col_index += 1

    def _get_all_records(self):
        self._refresh_headers()
        return self.sheet.get_all_records()

    def _get_row_index_by_id(self, row_id):
        if not row_id:
            return None

        col = self.col_map.get("RowID")
        if not col:
            return None

        values = self.sheet.col_values(col)

        for i, v in enumerate(values, start=1):
            if i == 1:
                continue
            if str(v).strip() == str(row_id).strip():
                return i

        return None

    def _ensure_row_id(self, row_index, row):
        col = self.col_map.get("RowID")
        if not col:
            return str(row_index)

        existing = str(row.get("RowID", "")).strip()

        if existing:
            return existing

        generated = str(row_index)
        self.sheet.update_cell(row_index, col, generated)
        return generated

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _normalize_media_field_value(self, key, value):
        if key in self.MEDIA_JSON_COLUMNS and isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)

        if value is None:
            return ""

        return str(value)

    def get_pending_rows(self):
        rows = self._get_all_records()
        result = []

        for idx, row in enumerate(rows, start=2):
            status = str(row.get("ProcessingStatus", "")).strip().lower()
            image_url = row.get("ImageURL")

            if status == "pending" and image_url:
                row_id = self._ensure_row_id(idx, row)

                result.append({
                    "RowID": row_id,
                    "ImageURL": image_url
                })

        return result

    def update_status(self, row_id, status):
        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

        row_index = self._get_row_index_by_id(row_id)
        if not row_index:
            raise ValueError(f"RowID not found: {row_id}")

        status_col = self.col_map.get("ProcessingStatus")
        if not status_col:
            raise ValueError("ProcessingStatus column not found")

        normalized_status = str(status or "").strip()

        self.sheet.update_cell(row_index, status_col, normalized_status)

        processing_started_col = self.col_map.get("ProcessingStartedAt")
        if processing_started_col:
            if normalized_status == "Processing":
                self.sheet.update_cell(
                    row_index,
                    processing_started_col,
                    self._now_iso(),
                )
            elif normalized_status == "Pending":
                self.sheet.update_cell(
                    row_index,
                    processing_started_col,
                    "",
                )

    def append_pending_product(self, image_url: str, price: Any):
        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

        required_columns = ["RowID", "ImageURL", "Price", "ProcessingStatus"]
        missing_columns = [col for col in required_columns if col not in self.col_map]

        if missing_columns:
            raise ValueError(
                f"Required sheet columns missing: {', '.join(missing_columns)}"
            )

        image_url_value = "" if image_url is None else str(image_url).strip()
        price_value = "" if price is None else str(price).strip()

        if not image_url_value:
            raise ValueError("image_url is required")

        if not price_value:
            raise ValueError("price is required")

        row_id = uuid.uuid4().hex
        row_values = ["" for _ in self.headers]

        row_values[self.col_map["RowID"] - 1] = row_id
        row_values[self.col_map["ImageURL"] - 1] = image_url_value
        row_values[self.col_map["Price"] - 1] = price_value
        row_values[self.col_map["ProcessingStatus"] - 1] = "Pending"

        if "SeedMediaType" in self.col_map:
            row_values[self.col_map["SeedMediaType"] - 1] = "image"

        if "SeedMediaURL" in self.col_map:
            row_values[self.col_map["SeedMediaURL"] - 1] = image_url_value

        if "SeedMediaStatus" in self.col_map:
            row_values[self.col_map["SeedMediaStatus"] - 1] = "temporary"

        self.sheet.append_row(row_values, value_input_option="USER_ENTERED")

        self._refresh_headers()
        row_index = self._get_row_index_by_id(row_id)

        if not row_index:
            raise RuntimeError("Failed to verify appended row in sheet")

        return {
            "row_id": row_id,
            "image_url": image_url_value,
            "status": "Pending",
        }

    def save_result(self, row_id, result: Any):
        if not isinstance(result, dict):
            raise ValueError("save_result expects a dict")

        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

        row_index = self._get_row_index_by_id(row_id)
        if not row_index:
            raise ValueError(f"RowID not found: {row_id}")

        for key in self.REQUIRED_RESULT_COLUMNS:
            col = self.col_map.get(key)
            if not col:
                continue

            value = result.get(key, "")

            self.sheet.update_cell(
                row_index,
                col,
                "" if value is None else str(value)
            )

    def update_media_fields(self, row_id, media_fields: Any):
        if not isinstance(media_fields, dict):
            raise ValueError("update_media_fields expects a dict")

        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

        row_index = self._get_row_index_by_id(row_id)
        if not row_index:
            raise ValueError(f"RowID not found: {row_id}")

        for key, value in media_fields.items():
            col = self.col_map.get(key)
            if not col or key not in self.MEDIA_COLUMNS:
                continue

            normalized_value = self._normalize_media_field_value(key, value)

            self.sheet.update_cell(
                row_index,
                col,
                normalized_value
            )
