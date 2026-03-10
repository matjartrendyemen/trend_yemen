import os
import time
import gspread
from dotenv import load_dotenv
from tenacity import retry, wait_fixed, stop_after_attempt
from google.oauth2.service_account import Credentials
from core_engine import BaseAdapter, audit_logger

load_dotenv()

class SheetsAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(name="GoogleSheets")
        self.sheet_id = os.getenv("SPREADSHEET_ID")
        self.client = None

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
    def _authenticate(self):
        try:
            creds = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/spreadsheets"])
            self.client = gspread.authorize(creds)
            audit_logger.log_event(self.name, "Auth", "success", "Access Granted")
            return True
        except Exception as e:
            if "429" in str(e):
                print("⚠️ Too many requests to Google Sheets, waiting 10 seconds before retry...")
                time.sleep(10)
                raise Exception("Retry due to 429 error")
            audit_logger.log_event(self.name, "Auth", "error", str(e))
            return False

    def read_data(self, range_name="A1:C10"):
        if not self.client:
            self._authenticate()
        sheet = self.client.open_by_key(self.sheet_id).sheet1
        return sheet.get(range_name)
