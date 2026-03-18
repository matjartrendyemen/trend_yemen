import json
import os
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials


class SheetsStore:
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

        self.headers = self.sheet.row_values(1)
        self.col_map = {name: idx + 1 for idx, name in enumerate(self.headers)}

    # -------------------------
    # Helpers
    # -------------------------
    def _get_all_records(self) -> List[Dict[str, Any]]:
        return self.sheet.get_all_records()

    def _get_row_index_by_id(self, row_id: Any) -> Optional[int]:
        if row_id is None or str(row_id).strip() == "":
            return None

        rowid_col = self.col_map.get("RowID")
        if not rowid_col:
            return None

        values = self.sheet.col_values(rowid_col)
        for i, value in enumerate(values, start=1):
            if i == 1:
                continue  # skip header row
            if str(value).strip() == str(row_id).strip():
                return i

        return None

    # -------------------------
    # Interface (for orchestrator)
    # -------------------------
    def get_pending_rows(self) -> List[Dict[str, Any]]:
        rows = self._get_all_records()
        result = []

        for row in rows:
            status = str(row.get("ProcessingStatus", "")).strip().lower()
            row_id = row.get("RowID")
            image_url = row.get("ImageURL")

            if status == "pending" and str(row_id).strip() and str(image_url).strip():
                result.append({
                    "RowID": row_id,
                    "ImageURL": image_url,
                })

        return result

    def update_status(self, row_id: Any, status: str):
        row_index = self._get_row_index_by_id(row_id)
        if row_index is None:
            raise ValueError(f"RowID not found or invalid: {row_id}")

        status_col = self.col_map.get("ProcessingStatus")
        if not status_col:
            raise ValueError("ProcessingStatus column not found")

        self.sheet.update_cell(row_index, status_col, status)

    def save_result(self, row_id: Any, result: Any):
        row_index = self._get_row_index_by_id(row_id)
        if row_index is None:
            raise ValueError(f"RowID not found or invalid: {row_id}")

        if not isinstance(result, dict):
            raise ValueError("save_result expects a dict of column names to values")

        updated_any = False
        for column_name, value in result.items():
            col_index = self.col_map.get(column_name)
            if not col_index:
                continue

            self.sheet.update_cell(row_index, col_index, "" if value is None else str(value))
            updated_any = True

        if not updated_any:
            raise ValueError("No matching sheet columns found in result payload")
