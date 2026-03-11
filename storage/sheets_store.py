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
            
            # التأكد من اسم الورقة (يجب أن يكون Products في الشيت لديك)
            self.products_sheet = self.spreadsheet.worksheet("Products")
            system_log.info(f"✅ Connected to Spreadsheet: {self.spreadsheet.title}")
        except Exception as e:
            system_log.critical(f"❌ Failed to connect to Google Sheets: {e}")
            raise

    def get_pending_rows(self):
        try:
            # جلب البيانات كقائمة لضمان التوافق مع ترتيب الأعمدة
            all_values = self.products_sheet.get_all_values()
            if not all_values or len(all_values) < 2:
                return []
            
            rows = all_values[1:]   # تجاوز صف العناوين
            pending_tasks = []
            
            for index, row in enumerate(rows):
                row_number = index + 2
                # ترتيب الأعمدة: A(0), B(1)=ImageURL, C(2)=Status
                image_url = row[1] if len(row) > 1 else ""
                status = row[2] if len(row) > 2 else ""

                if str(status).strip().lower() == 'pending':
                    pending_tasks.append({
                        'index': row_number,
                        'image_url': image_url,
                        'status': status
                    })
            
            system_log.info(f"🔍 Scan complete. Found {len(pending_tasks)} pending tasks.")
            return pending_tasks
        except Exception as e:
            system_log.error(f"❌ Error fetching from sheets: {e}")
            return []

    def update_status(self, row_id, status):
        """تحديث عمود الحالة (العمود C)"""
        try:
            self.products_sheet.update_acell(f'C{row_id}', status)
            system_log.info(f"📝 Row {row_id} status updated to: {status}")
        except Exception as e:
            system_log.error(f"❌ Failed to update status for row {row_id}: {e}")

    def update_result(self, row_id, result_text):
        """تحديث عمود النتائج (العمود D)"""
        try:
            self.products_sheet.update_acell(f'D{row_id}', result_text)
            system_log.info(f"💾 Row {row_id} results written to Column D.")
        except Exception as e:
            system_log.error(f"❌ Failed to update results for row {row_id}: {e}")

    # دوال إضافية للتوافق مع المحرك
    def mark_processing(self, row_id): self.update_status(row_id, "Processing")
    def mark_completed(self, row_id, link=""): 
        self.update_status(row_id, "Completed")
        if link: self.update_result(row_id, link)
    def mark_failed(self, row_id, msg): self.update_status(row_id, f"Failed: {msg}")
