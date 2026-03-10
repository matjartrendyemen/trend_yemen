import os
import json
import gspread
from monitoring.logger import system_log

class SheetsStore:
    def __init__(self):
        system_log.info("Booting up Google Sheets Store...")
        try:
            creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
            if not creds_json_str:
                raise ValueError("GOOGLE_CREDENTIALS missing.")
            
            creds_dict = json.loads(creds_json_str)
            self.client = gspread.service_account_from_dict(creds_dict)
            self.sheet_id = os.getenv("SPREADSHEET_ID")
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            self.products_sheet = self.spreadsheet.worksheet("Products")
            system_log.info("Google Sheets connected successfully.")
        except Exception as e:
            system_log.critical(f"Failed to connect to Google Sheets: {e}")
            raise

    def get_pending_rows(self):
        try:
            records = self.products_sheet.get_all_records()
            pending_tasks = []
            for index, row in enumerate(records):
                if str(row.get('ProcessingStatus', '')).strip().lower() == 'pending':
                    pending_tasks.append({
                        'RowID': index + 2,
                        'ImageURL': row.get('ImageURL', ''),
                        'ProductName': row.get('ProductName', 'Trending Item')
                    })
            return pending_tasks
        except Exception as e:
            system_log.error(f"Error fetching from sheets: {e}")
            return []

    def mark_processing(self, row_id):
        self.products_sheet.update_acell(f'C{row_id}', 'Processing')

    def mark_completed(self, row_id, drive_link=""):
        self.products_sheet.update_acell(f'C{row_id}', 'Completed')
        if drive_link:
            self.products_sheet.update_acell(f'D{row_id}', drive_link)

    def mark_failed(self, row_id, error_msg):
        self.products_sheet.update_acell(f'C{row_id}', f'Failed: {error_msg}')
