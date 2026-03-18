import time

from services.ai_service import AIService
from storage.sheets_store import SheetsStore


class MasterOrchestrator:
    def __init__(self):
        self.ai_service = AIService()
        self.sheets = SheetsStore()

        self.poll_interval = 5
        self.processing_delay = 2

    def run(self):
        print("📡 Orchestrator started...")

        while True:
            try:
                pending_rows = self.sheets.get_pending_rows()

                if not pending_rows:
                    time.sleep(self.poll_interval)
                    continue

                for row in pending_rows:
                    self.process_row(row)

            except Exception as e:
                print(f"❌ Orchestrator loop error: {e}")
                time.sleep(self.poll_interval)

    def process_row(self, row):
        row_id = row.get("RowID")
        image_url = row.get("ImageURL")

        if not row_id or not image_url:
            print(f"⚠️ Skipping invalid row: {row}")
            return

        try:
            print(f"🔄 Processing row {row_id}")

            self.sheets.update_status(row_id, "Processing")

            result = self.ai_service.process_image(image_url)

            self.sheets.save_result(row_id, result)

            self.sheets.update_status(row_id, "Completed")

            print(f"✅ Completed row {row_id}")

        except Exception as e:
            print(f"❌ Failed row {row_id}: {e}")

            try:
                self.sheets.update_status(row_id, "Failed")
            except Exception as inner_error:
                print(f"❌ Failed to update status for row {row_id}: {inner_error}")

        finally:
            time.sleep(self.processing_delay)
