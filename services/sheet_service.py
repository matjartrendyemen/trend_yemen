import os
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetService:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file('config/service_account.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        
        # استخدام المتغير الصحيح واسم التبويب Products
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet("Products")

    def get_next_task(self):
        """يبحث عن المهام المعلقة في عمود ProcessingStatus"""
        all_records = self.sheet.get_all_records()
        system_log.info(f"📋 Sheet Check: Found {len(all_records)} products.")
        
        for index, row in enumerate(all_records, start=2):
            # التأكد من مطابقة اسم العمود ProcessingStatus تماماً
            status = str(row.get('ProcessingStatus', '')).strip().lower()
            if status == 'pending':
                system_log.info(f"🎯 Found Pending task at row {index}")
                return {"row": index, "data": row}
        
        return None

    def update_status(self, row_index, status_text):
        # تحديث العمود C (رقم 3) الذي يمثل ProcessingStatus في صورتك
        self.sheet.update_cell(row_index, 3, status_text)
        system_log.info(f"✅ Row {row_index} status updated to: {status_text}")
