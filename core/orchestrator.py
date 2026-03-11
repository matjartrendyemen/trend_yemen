import time
import os
from flask import Flask
from threading import Thread
from services.ai_service import AIService
from storage.sheets_store import SheetsStore

# --- إعداد Flask لإبقاء Railway مستيقظاً ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Trend Store Bot is Active 🚀", 200

def run_flask():
    # Railway يستخدم المتغير البيئي PORT تلقائياً
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- كلاس المحرك الأساسي مع خاصية التوقيت ---
class MasterOrchestrator:
    def __init__(self):
        self.ai = AIService()
        self.store = SheetsStore()
        self.wait_time = 120  # الفحص كل دقيقتين
        self.timeout = 45     # مهلة معالجة الصف الواحدة

    def run_forever(self):
        print("🚀 Master Orchestrator starting with Flask & Timeout protection...")
        while True:
            try:
                # 1. جلب الصفوف المطلوب معالجتها
                pending_rows = self.store.get_pending_rows()
                
                if not pending_rows:
                    print("😴 No tasks found. Sleeping...")
                else:
                    for row in pending_rows:
                        print(f"🎯 Task found at row {row['index']}")
                        
                        # تغيير الحالة فوراً لمنع التكرار
                        self.store.update_status(row['index'], "Processing")
                        
                        # معالجة الصف مع مراعاة الوقت
                        success = self.process_with_timeout(row)
                        
                        if success:
                            print(f"✅ Row {row['index']} Completed.")
                        else:
                            print(f"⚠️ Row {row['index']} failed or timed out.")
                            self.store.update_status(row['index'], "Failed/Timeout")

                        # "وقت تنفس" قصير بين الصفوف لتجنب Quota Hit
                        time.sleep(20)

            except Exception as e:
                print(f"❌ Error in Main Loop: {e}")
            
            time.sleep(self.wait_time)

    def process_with_timeout(self, row):
        """دالة معالجة الصف مع حماية من التعليق"""
        try:
            # تحليل الصورة عبر جيمني
            keywords = self.ai.analyze_product_image(row['image_url'])
            
            if keywords:
                # تحديث الشيت بالنتائج
                self.store.update_result(row['index'], keywords)
                self.store.update_status(row['index'], "Completed")
                return True
        except Exception as e:
            print(f"Error processing row {row['index']}: {e}")
        return False

if __name__ == "__main__":
    # تشغيل Flask في خيط (Thread) منفصل
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # تشغيل المحرك الأساسي
    orchestrator = MasterOrchestrator()
    orchestrator.run_forever()
