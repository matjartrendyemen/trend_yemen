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
                rows = self.sheets.get_pending_rows()

                if not rows:
                    time.sleep(self.poll_interval)
                    continue

                for row in rows:
                    self.process_row(row)

            except Exception as e:
                print(f"❌ Loop error: {e}")
                time.sleep(self.poll_interval)

    def process_row(self, row):
        row_id = row.get("RowID")
        image_url = row.get("ImageURL")

        if not row_id or not image_url:
            print(f"⚠️ Invalid row skipped: {row}")
            return

        try:
            print(f"🔄 Processing RowID={row_id}")

            self.sheets.update_status(row_id, "Processing")

            result = self.ai_service.process_image(image_url)

            print(f"🧠 AI Result RowID={row_id}: {result}")

            self.sheets.save_result(row_id, result)

            quality_status = result.get("QualityStatus")

            if quality_status == "Failed":
                final_status = "Failed"
            elif quality_status in ["Accepted", "NeedsReview"]:
                final_status = "Completed"
            else:
                final_status = "Failed"

            print(f"📊 Final Status RowID={row_id}: {final_status}")

            self.sheets.update_status(row_id, final_status)

        except Exception as e:
            print(f"❌ Exception RowID={row_id}: {e}")
            self.sheets.update_status(row_id, "Failed")

        finally:
            time.sleep(self.processing_delay)
