import time
import traceback
from monitoring.logger import system_log
from services.ai_service import AIService

class MasterOrchestrator:
    def __init__(self):
        system_log.info("Initializing Master Orchestrator...")
        self.ai = AIService()
        self.is_running = True

    def process_pending_row(self, row):
        row_id = row.get("RowID")
        image_url = row.get("ImageURL")
        fallback_text = row.get("ProductName", "Trending Items")
        try:
            keywords = self.ai.get_search_keywords(image_url, fallback_text)
            system_log.info(f"Row {row_id} processed successfully with keywords: {keywords}")
        except Exception as e:
            system_log.error(f"Failed to process Row {row_id}: {str(e)}")
            system_log.debug(traceback.format_exc())

    def run_forever(self):
        system_log.info("System is now AUTONOMOUS and running forever.")
        while self.is_running:
            try:
                pending_rows = []  # محاكاة
                if not pending_rows:
                    time.sleep(30)
                    continue
                for row in pending_rows:
                    self.process_pending_row(row)
                    time.sleep(5)
            except Exception as e:
                system_log.critical(f"Orchestrator crashed! Auto-recovering in 60s. Error: {e}")
                time.sleep(60)
