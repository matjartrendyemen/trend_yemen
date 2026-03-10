import os
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetService:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # تأكد من وجود ملف المفاتيح في المسار الصحيح
        self.creds = Credentials.from_service_account_file('config/service_account.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet_id = os.getenv("SHEET_ID")
        self.sheet = self.client.open_by_key(self.sheet_id).sheet1

    def get_next_task(self):
        """يبحث عن أول سطر حالته Pending"""
        all_records = self.sheet.get_all_records()
        system_log.info(f"📋 Checking Sheet: Found {len(all_records)} total rows.")
        
        for index, row in enumerate(all_records, start=2):
            # جعل البحث لا يتأثر بحالة الأحرف (Pending vs pending)
            status = str(row.get('Status', '')).strip().lower()
            if status == 'pending':
                system_log.info(f"🎯 Task Found at row {index}!")
                return {"row": index, "data": row}
        
        system_log.info("😴 No 'Pending' tasks found right now.")
        return None

    def update_status(self, row_index, status_text):
        # تأكد أن عمود الحالة هو العمود رقم 4 (أو عدله حسب ترتيبك)
        # سنفترض أن Status هو العمود D (رقم 4)
        self.sheet.update_cell(row_index, 4, status_text)
        system_log.info(f"📝 Row {row_index} updated to: {status_text}")
