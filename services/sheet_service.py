import os
import json
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetService:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # التعديل هنا ليتطابق مع صورتك: GOOGLE_CREDENTIALS
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        
        if not creds_json:
            system_log.error("❌ GOOGLE_CREDENTIALS variable is missing!")
            raise ValueError("Missing GOOGLE_CREDENTIALS in environment")

        info = json.loads(creds_json)
        self.creds = Credentials.from_service_account_info(info, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        
        # التأكد من SPREADSHEET_ID واسم التبويب Products
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet("Products")

    def get_next_task(self):
        all_values = self.sheet.get_all_values()
        if len(all_values) <= 1: return None
        
        # [span_3](start_span)البحث في العمود C (رقم 3) عن حالة Pending[span_3](end_span)
        for index, row in enumerate(all_values[1:], start=2):
            if len(row) >= 3:
                status = str(row[2]).strip().lower()
                if status == 'pending':
                    system_log.info(f"🎯 Task found at row {index}")
                    return {"row": index, "image_url": row[1]}
        return None

    def update_status(self, row_index, status_text):
        # [span_4](start_span)تحديث العمود C (رقم 3) للحالة[span_4](end_span)
        self.sheet.update_cell(row_index, 3, status_text)
        system_log.info(f"📝 Row {row_index} status -> {status_text}")
