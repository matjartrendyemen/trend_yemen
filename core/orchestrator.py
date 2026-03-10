import time
import traceback
from monitoring.logger import system_log
from services.ai_service import AIService
from storage.sheets_store import SheetsStore
from storage.drive_store import DriveStore
from adapters.cj_adapter import CJAdapter

class MasterOrchestrator:
    def __init__(self):
        system_log.info("Booting Master Orchestrator...")
        self.ai = AIService()
        self.sheets = SheetsStore()
        self.drive = DriveStore()
        self.cj = CJAdapter()
        self.is_running = True

    def process_pending_row(self, row):
        row_id = row.get("RowID")
        image_url = str(row.get("ImageURL", "")).strip()
        fallback_text = row.get("ProductName", "Trending Item") 

        try:
            if not image_url or not image_url.startswith("http"):
                system_log.warning(f"Row {row_id} skipped: Invalid or Missing Image URL.")
                self.sheets.mark_failed(row_id, "Missing Image URL")
                return

            self.sheets.mark_processing(row_id)
            system_log.info(f"--- Processing Row {row_id} ---")

            keywords = self.ai.get_search_keywords(image_url, fallback_text)
            product_data = self.cj.fetch_product(keywords)
            drive_link = self.drive.create_folder(product_data['sku'], product_data['title'])
            self.sheets.mark_completed(row_id, drive_link)

            system_log.info(f"--- Row {row_id} Completed! ---")
        except Exception as e:
            system_log.error(f"Error Row {row_id}: {str(e)}")
            self.sheets.mark_failed(row_id, str(e))

    def run_forever(self):
        system_log.info("Bot is Active and Safe.")
        while self.is_running:
            try:
                pending_rows = self.sheets.get_pending_rows()
                if not pending_rows:
                    time.sleep(30)
                    continue
                for row in pending_rows:
                    self.process_pending_row(row)
                    time.sleep(5)
            except Exception as e:
                system_log.critical(f"System Crash: {e}")
                time.sleep(60)
