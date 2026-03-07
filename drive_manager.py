import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class GoogleDriveManager:
    def __init__(self):
        print("[GOOGLE_DRIVE] Booting up connection...")
        creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json_str:
            raise ValueError("CRITICAL: GOOGLE_CREDENTIALS missing.")
        creds_dict = json.loads(creds_json_str)
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_info(creds_dict, scopes=self.scopes)
        self.service = build('drive', 'v3', credentials=self.creds)
        self.parent_folder_id = os.getenv("DRIVE_FOLDER_ID")

    def create_product_folder(self, sku: str, title: str) -> dict:
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        folder_name = f"{sku} - {safe_title}"[:50]
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.parent_folder_id]
        }
        folder = self.service.files().create(body=folder_metadata, fields='id, webViewLink').execute()
        folder_id = folder.get('id')
        self.service.permissions().create(
            fileId=folder_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        return {'id': folder_id, 'link': folder.get('webViewLink')}
