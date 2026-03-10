import time
import traceback
from monitoring.logger import system_log
from services.ai_service import AIService
from storage.sheets_store import SheetsStore
from storage.drive_store import DriveStore
from adapters.cj_adapter import CJAdapter

class MasterOrchestrator:
    def __init__(self):
        system_log.info("Initializing Master Orchestrator (Enterprise Mode)...")
        self.ai = AIService()
        self.sheets = SheetsStore()
        self.drive = DriveStore()
        self.cj = CJAdapter()
        self.is_running = True

    def process_pending_row(self, row):
        row_id = row.get("RowID")
        image_url = row.get("ImageURL")
        fallback_text = row.get("ProductName", "Trending Items") 

        try:
            self.sheets.mark_processing(row_id)
            system_log.info(f"--- Started processing Row {row_id} ---")

            keywords = self.ai.get_search_keywords(image_url, fallback_text)
            product_data = self.cj.fetch_product(keywords)
            drive_link = self.drive.create_folder(product_data['sku'], product_data['title'])
            self.sheets.mark_completed(row_id, drive_link)

            system_log.info(f"--- Row {row_id} processed successfully! ---")
        except Exception as e:
            system_log.error(f"Failed to process Row {row_id}: {str(e)}")
            system_log.debug(traceback.format_exc())
            self.sheets.mark_failed(row_id, str(e))

    def run_forever(self):
        system_log.info("System is now AUTONOMOUS and polling Google Sheets.")
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
                system_log.critical(f"Orchestrator crashed! Auto-recovering in 60s. Error: {e}")
                time.sleep(60)
