import time
from services.sheet_service import SheetService
from services.ai_service import AIService
from monitoring.logger import system_log

class MasterOrchestrator:
    def __init__(self):
        self.sheets = SheetService()
        self.ai = AIService()

    def start_monitoring(self):
        system_log.info("🚀 Master Orchestrator running in FREE TIER mode...")
        while True:
            try:
                task = self.sheets.get_next_task()
                if task:
                    row_id = task['row']
                    img_url = task['image_url']
                    
                    self.sheets.update_status(row_id, "Processing")
                    
                    # تحليل الصورة
                    keywords = self.ai.analyze_product_image(img_url)
                    
                    # تحديث الشيت بالنتيجة في العمود D
                    self.sheets.sheet.update_cell(row_id, 4, keywords)
                    self.sheets.update_status(row_id, "Completed")
                    
                    # انتظر دقيقة كاملة بعد كل صورة لمنح الـ API فرصة للتنفس
                    system_log.info("⏳ Cooling down for 60s after processing...")
                    time.sleep(60)
                
                # فحص الشيت كل دقيقتين بدلاً من 10 ثوانٍ
                time.sleep(120) 
            except Exception as e:
                system_log.error(f"❌ Loop Error: {e}")
                time.sleep(180) # انتظر 3 دقائق إذا حدث خطأ
