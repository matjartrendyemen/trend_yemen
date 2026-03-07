import os
import json
import gspread

class GoogleSheetsProductRepository:
    def __init__(self):
        print("[GOOGLE_SHEETS] Booting up connection...")
        creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json_str:
            raise ValueError("CRITICAL: GOOGLE_CREDENTIALS is missing in environment variables.")
        creds_dict = json.loads(creds_json_str)
        self.client = gspread.service_account_from_dict(creds_dict)
        sheet_id = os.getenv("SPREADSHEET_ID")
        if not sheet_id:
            raise ValueError("CRITICAL: SPREADSHEET_ID is missing.")
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self.products_sheet = self.spreadsheet.worksheet("Products")

    def get_pending_products_with_categories(self):
        records = self.products_sheet.get_all_records()
        pending_tasks = []
        for index, row in enumerate(records):
            if str(row.get('ProcessingStatus', '')).strip().lower() == 'pending':
                task = {'RowID': index + 2, 'ImageURL': row.get('ImageURL', '')}
                pending_tasks.append(task)
        return pending_tasks

    def update_product_status(self, row_id: int, status: str, drive_link: str = ""):
        self.products_sheet.update_acell(f'C{row_id}', status)
        if drive_link:
            self.products_sheet.update_acell(f'D{row_id}', drive_link)
