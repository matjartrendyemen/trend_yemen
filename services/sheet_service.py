import os
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetService:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file('config/service_account.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        
        # المتغير الصحيح حسب ما أرسلت هو SPREADSHEET_ID
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet("Products")

    def get_next_task(self):
        """يبحث عن أول سطر حالته Pending في عمود ProcessingStatus"""
        all_records = self.sheet.get_all_records()
        system_log.info(f"📋 Checking Sheet: Found {len(all_records)} total rows.")
        
        for index, row in enumerate(all_records, start=2):
            # استخدام اسم العمود الصحيح ProcessingStatus كما في الصورة
            status = str(row.get('ProcessingStatus', '')).strip().lower()
            if status == 'pending':
                system_log.info(f"🎯 Task Found at row {index}!")
                return {"row": index, "data": row}
        
        system_log.info("😴 No 'Pending' tasks found in ProcessingStatus.")
        return None

    def update_status(self, row_index, status_text):
        # سنحدث العمود B (رقم 2) الذي يمثل ProcessingStatus حسب الصورة
        self.sheet.update_cell(row_index, 2, status_text)
        system_log.info(f"📝 Row {row_index} status updated to: {status_text}")
