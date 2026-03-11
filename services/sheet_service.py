import os
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetService:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file('config/service_account.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        # الدخول لتبويب Products مباشرة
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet("Products")

    def get_next_task(self):
        """قراءة جميع القيم والبحث عن Pending في العمود C"""
        all_values = self.sheet.get_all_values()
        system_log.info(f"📋 Total rows found: {len(all_values)}")
        
        # نبدأ من السطر الثاني لتخطي العناوين
        for index, row in enumerate(all_values[1:], start=2):
            if len(row) >= 3:
                status = str(row[2]).strip().lower() # العمود C هو index 2
                if status == 'pending':
                    system_log.info(f"🎯 Task Found at row {index}!")
                    return {
                        "row": index,
                        "image_url": row[1], # العمود B هو الرابط
                        "data": row
                    }
        system_log.info("😴 No 'pending' tasks in column C.")
        return None

    def update_status(self, row_index, status_text):
        # تحديث العمود C (رقم 3)
        self.sheet.update_cell(row_index, 3, status_text)
        system_log.info(f"📝 Row {row_index} set to {status_text}")
