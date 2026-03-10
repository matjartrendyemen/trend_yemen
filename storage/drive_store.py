import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from monitoring.logger import system_log

class DriveStore:
    def __init__(self):
        system_log.info("Booting up Google Drive Store...")
        try:
            creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
            creds_dict = json.loads(creds_json_str)
            self.scopes = ['https://www.googleapis.com/auth/drive']
            self.creds = Credentials.from_service_account_info(creds_dict, scopes=self.scopes)
            self.service = build('drive', 'v3', credentials=self.creds)
            self.parent_folder_id = os.getenv("DRIVE_FOLDER_ID")
        except Exception as e:
            system_log.critical(f"Failed to connect to Google Drive: {e}")
            raise

    def create_folder(self, sku: str, title: str) -> str:
        try:
            safe_title = "".join([c for c in title if c.isalnum() or c==' ']).rstrip()
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
            
            system_log.info(f"Created Drive folder for SKU: {sku}")
            return folder.get('webViewLink')
        except Exception as e:
            system_log.error(f"Failed to create Drive folder: {e}")
            return ""
