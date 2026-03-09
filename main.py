import time
import os
import traceback
from dotenv import load_dotenv
from flask import Flask

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
            if 'row_id' in locals():
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
            except Exception as e:
                time.sleep(60)

app = Flask(__name__)
bot = AutonomousController()

@app.route("/")
def home():
    return "✅ Bot is running on Port 5000 and connected to Google Sheets!"

if __name__ == "__main__":
    import threading
    threading.Thread(target=bot.start_infinite_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
