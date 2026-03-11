import time
from services.sheet_service import SheetService
from services.ai_service import AIService
from monitoring.logger import system_log

class MasterOrchestrator:
    def __init__(self):
        self.sheets = SheetService()
        self.ai = AIService()

    def start_monitoring(self):
        system_log.info("🚀 Master Orchestrator is running...")
        while True:
            try:
                task = self.sheets.get_next_task()
                if task:
                    row_id = task['row']
                    img_url = task['image_url']
                    
                    self.sheets.update_status(row_id, "Processing")
                    
                    # تحليل الصورة
                    keywords = self.ai.analyze_product_image(img_url)
                    
                    # تحديث الشيت بالنتيجة (سنضع الكلمات في العمود D مثلاً)
                    self.sheets.sheet.update_cell(row_id, 4, keywords)
                    self.sheets.update_status(row_id, "Completed")
                
                time.sleep(10) # فحص كل 10 ثوانٍ
            except Exception as e:
                system_log.error(f"❌ Loop Error: {e}")
                time.sleep(30)
