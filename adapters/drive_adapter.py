import os
import time
from dotenv import load_dotenv
from tenacity import retry, wait_fixed, stop_after_attempt
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from core_engine import BaseAdapter, audit_logger

load_dotenv()

class DriveAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(name="GoogleDrive")
        self.folder_id = os.getenv("DRIVE_FOLDER_ID")
        self.service = None

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
    def _authenticate(self):
        try:
            creds = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/drive"])
            self.service = build("drive", "v3", credentials=creds)
            audit_logger.log_event(self.name, "Auth", "success", "Access Granted")
            return True
        except Exception as e:
            if "429" in str(e):
                print("⚠️ Too many requests to Google Drive, waiting 10 seconds before retry...")
                time.sleep(10)
                raise Exception("Retry due to 429 error")
            audit_logger.log_event(self.name, "Auth", "error", str(e))
            return False

    def list_files(self):
        if not self.service:
            self._authenticate()
        results = self.service.files().list(q=f"'{self.folder_id}' in parents", pageSize=10).execute()
        return results.get("files", [])
