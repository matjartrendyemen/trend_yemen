import json
import os
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

    def __init__(self):
        self.sheet_name = "Products"

        creds_raw = os.getenv("GOOGLE_CREDENTIALS")
        spreadsheet_id = os.getenv("SPREADSHEET_ID")

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
        missing_columns = [
            col for col in self.REQUIRED_RESULT_COLUMNS if col not in self.col_map
        ]

        if not missing_columns:
            return

        next_col_index = len(self.headers) + 1

        for column_name in missing_columns:
            self.sheet.update_cell(1, next_col_index, column_name)
            next_col_index += 1

    def _get_all_records(self):
        return self.sheet.get_all_records()

    def _get_row_index_by_id(self, row_id):
        if not row_id:
            return None

        col = self.col_map.get("RowID")
        values = self.sheet.col_values(col)

        for i, v in enumerate(values, start=1):
            if i == 1:
                continue
            if str(v).strip() == str(row_id).strip():
                return i

        raise ValueError(f"RowID not found: {row_id}")

    def _ensure_row_id(self, row_index, row):
        col = self.col_map.get("RowID")
        existing = str(row.get("RowID", "")).strip()

        if existing:
            return existing

        generated = str(row_index)
        self.sheet.update_cell(row_index, col, generated)
        return generated

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
        row_index = self._get_row_index_by_id(row_id)
        col = self.col_map.get("ProcessingStatus")
        self.sheet.update_cell(row_index, col, status)

    def save_result(self, row_id, result: Any):
        if not isinstance(result, dict):
            raise ValueError("save_result expects a dict")

        self._refresh_headers()
        self._ensure_required_columns()
        self._refresh_headers()

        row_index = self._get_row_index_by_id(row_id)

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
