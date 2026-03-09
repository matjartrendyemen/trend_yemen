import time
import os
import traceback
from dotenv import load_dotenv
from flask import Flask

# استيراد الوحدات
from core_engine import audit_logger, StandardProduct
from vision_adapter import SmartVisionAdapter
from cj_adapter import CJAdapter
from google_repository import GoogleSheetsProductRepository
from drive_manager import GoogleDriveManager

load_dotenv()

class AutonomousController:
    def __init__(self):
        audit_logger.log_event("SYSTEM_CONTROLLER", "Initialization", "info", "Booting up PRODUCTION Agentic Loop...")
        self.vision = SmartVisionAdapter(name="VisionUnit")
        self.cj_api = CJAdapter()
        self.sheets = GoogleSheetsProductRepository()
        self.drive = GoogleDriveManager()
        self.poll_interval = 30

    def run_cycle(self):
        try:
            pending_tasks = self.sheets.get_pending_products_with_categories()
            if not pending_tasks or len(pending_tasks) == 0:
                return False
            current_task = pending_tasks[0]
            row_id = current_task.get('RowID')
            image_url = current_task.get('ImageURL')
            if not image_url:
                self.sheets.update_product_status(row_id, "Error: No Image")
                return True
            self.sheets.update_product_status(row_id, "Processing")
        except Exception as e:
            return False

        try:
            keywords = self.vision.extract_keywords(image_url)
            product = self.cj_api.execute(keywords)
            if not product:
                raise ValueError("CJ API failed to return a product.")
            if getattr(product, 'completeness_score', 0) < 100.0:
                product = self.vision.heal_product_data(product)
            folder_info = self.drive.create_product_folder(product.sku, product.title)
            self.sheets.update_product_status(row_id, "Completed", folder_info.get('link', ''))
            return True
        except Exception as e:
            self.sheets.update_product_status(row_id, f"Failed: {str(e)}")
            return True

    def start_infinite_loop(self):
        while True:
            try:
                task_processed = self.run_cycle()
                if not task_processed:
                    time.sleep(self.poll_interval)
                else:
                    time.sleep(5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                time.sleep(60)

# إضافة واجهة ويب بسيطة
app = Flask(__name__)
bot = AutonomousController()

@app.route("/")
def home():
    return "✅ Bot is running and connected to Google Sheets!"

if __name__ == "__main__":
    import threading
    threading.Thread(target=bot.start_infinite_loop, daemon=True).start()
    # تعديل البورت ليقرأ من البيئة أو يستخدم 8080 افتراضيًا
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
