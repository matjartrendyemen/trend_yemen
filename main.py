import time
import os
import traceback
from dotenv import load_dotenv

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

        # 🟢 تم تفعيل الربط الحقيقي مع جوجل شيتس ودرايف
        self.sheets = GoogleSheetsProductRepository()
        self.drive = GoogleDriveManager()

        self.poll_interval = 30  # يبحث في الشيت كل 30 ثانية

    def run_cycle(self):
        """الدورة المستقلة لمعالجة منتج واحد من Google Sheets"""

        audit_logger.log_event("SYSTEM_CONTROLLER", "Polling", "info", "Checking Google Sheets for pending images...")

        try:
            # 1. جلب أول صف حالته Pending
            pending_tasks = self.sheets.get_pending_products_with_categories()
            if not pending_tasks or len(pending_tasks) == 0:
                return False  # لا يوجد مهام، ينام قليلاً

            current_task = pending_tasks[0]
            row_id = current_task.get('RowID')
            image_url = current_task.get('ImageURL')  # تأكد أن اسم العمود في الشيت هو ImageURL

            if not image_url:
                self.sheets.update_product_status(row_id, "Error: No Image")
                return True

            audit_logger.log_event("SYSTEM_CONTROLLER", "Task Found", "info", f"Processing Row {row_id}")

            # قفل الصف فوراً لمنع التكرار
            self.sheets.update_product_status(row_id, "Processing")

        except Exception as e:
            audit_logger.log_event("SHEETS_API", "Error", "error", f"Failed to read sheets: {str(e)}")
            return False

        try:
            # 2. تحليل الصورة واستخراج الكلمات المفتاحية
            audit_logger.log_event("VISION_UNIT", "Analyze", "info", f"Analyzing image from row {row_id}")
            keywords = self.vision.extract_keywords(image_url)

            # 3. جلب المنتج من CJ API
            audit_logger.log_event("CJ_API", "Fetch", "info", f"Searching CJ for: {keywords}")
            product = self.cj_api.execute(keywords)

            if not product:
                raise ValueError("CJ API failed to return a product.")

            # 4. ترميم البيانات إذا كان التقييم أقل من 100%
            if getattr(product, 'completeness_score', 0) < 100.0:
                audit_logger.log_event("HEALING_UNIT", "Auto-Fix", "warning", "Healing missing data...")
                product = self.vision.heal_product_data(product)

            # 5. الحفظ في درايف وتحديث الشيت
            audit_logger.log_event("STORAGE_UNIT", "Save", "info", f"Saving product {product.sku} to Drive.")
            folder_info = self.drive.create_product_folder(product.sku, product.title)

            # تحديث الشيت بالنجاح ورابط الدرايف
            self.sheets.update_product_status(row_id, "Completed", folder_info.get('link', ''))

            audit_logger.log_event("SYSTEM_CONTROLLER", "Cycle Complete", "success", f"Row {row_id} finished 100%.")
            return True

        except Exception as e:
            error_details = str(e)
            audit_logger.log_event("SYSTEM_CONTROLLER", "Cycle Failed", "error", f"Row {row_id} failed: {error_details}")
            # إذا فشل، نكتب سبب الفشل في الشيت
            self.sheets.update_product_status(row_id, f"Failed: {error_details}")
            return True

    def start_infinite_loop(self):
        audit_logger.log_event("SYSTEM_CONTROLLER", "Live", "success", "Agent is now LIVE and checking Google Sheets.")
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
                audit_logger.log_event("FATAL_CRASH", "Loop Restart", "critical", str(e))
                time.sleep(60)

if __name__ == "__main__":
    bot = AutonomousController()
    bot.start_infinite_loop()
