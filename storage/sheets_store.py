import os
import json
import gspread
from google.oauth2.service_account import Credentials
from monitoring.logger import system_log

class SheetsStore:
    def __init__(self):
        system_log.info("🚀 Booting up Unified Sheets Service...")
        try:
            self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_json = os.getenv("GOOGLE_CREDENTIALS")
            
            if not creds_json:
                system_log.error("❌ GOOGLE_CREDENTIALS missing!")
                raise ValueError("Missing GOOGLE_CREDENTIALS in environment")

            info = json.loads(creds_json)
            # استخدام Credentials الصحيحة لضمان صلاحيات الكتابة
            self.creds = Credentials.from_service_account_info(info).with_scopes(self.scope)
            self.client = gspread.authorize(self.creds)
            
            self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            self.products_sheet = self.spreadsheet.worksheet("Products")
            system_log.info(f"✅ Connected to Sheet: {self.spreadsheet.title}")
        except Exception as e:
            system_log.critical(f"❌ Connection Failed: {e}")
            raise

    def get_pending_rows(self):
        """جلب المهام المتوفرة - متوافق مع الأوركستريتور"""
        try:
            all_values = self.products_sheet.get_all_values()
            if len(all_values) <= 1: return []
            
            pending_tasks = []
            # العمود B هو index 1، العمود C هو index 2
            for index, row in enumerate(all_values[1:], start=2):
                if len(row) >= 3:
                    status = str(row[2]).strip().lower()
                    if status == 'pending':
                        pending_tasks.append({
                            "index": index, 
                            "image_url": row[1]
                        })
            
            if pending_tasks:
                system_log.info(f"🔍 Found {len(pending_tasks)} pending tasks.")
            return pending_tasks
        except Exception as e:
            system_log.error(f"❌ Error fetching rows: {e}")
            return []

    def update_status(self, row_index, status_text):
        """تحديث العمود C"""
        try:
            self.products_sheet.update_cell(row_index, 3, status_text)
            system_log.info(f"📝 Row {row_index} status -> {status_text}")
        except Exception as e:
            system_log.error(f"❌ Failed status update: {e}")

    def update_result(self, row_index, result_text):
        """تحديث العمود D بالنتائج"""
        try:
            self.products_sheet.update_cell(row_index, 4, result_text)
            system_log.info(f"💾 Row {row_index} results saved to Column D.")
        except Exception as e:
            system_log.error(f"❌ Failed result update: {e}")

    # توفير التوافق مع الدوال القديمة
    def mark_processing(self, r_id): self.update_status(r_id, "Processing")
    def mark_completed(self, r_id, res=""): 
        self.update_status(r_id, "Completed")
        if res: self.update_result(r_id, res)
