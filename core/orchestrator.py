import time
import os
from flask import Flask
from threading import Thread
from services.ai_service import AIService
from storage.sheets_store import SheetsStore

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Trend Store Bot is Active 🚀", 200

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

class MasterOrchestrator:
    def __init__(self):
        self.ai = AIService()
        self.store = SheetsStore()
        self.wait_time = 30  # خفضنا وقت الفحص لـ 30 ثانية لتسريع التجربة

    def run_forever(self):
        print("🚀 المحرك يعمل الآن بذكاء مرن...")
        while True:
            try:
                pending_rows = self.store.get_pending_rows()
                
                if not pending_rows:
                    print("😴 لا توجد مهام حالياً. سأفحص مجدداً بعد قليل...")
                else:
                    for row in pending_rows:
                        # جعل الفحص مرناً (تحويل الكل لحروف صغيرة)
                        print(f"🎯 تم العثور على مهمة في الصف {row['index']}")
                        
                        self.store.update_status(row['index'], "Processing")
                        
                        # تحليل الصورة
                        result = self.ai.analyze_product_image(row['image_url'])
                        
                        if result and "Error" not in result:
                            self.store.update_result(row['index'], result)
                            self.store.update_status(row['index'], "Completed")
                            print(f"✅ تم بنجاح معالجة الصف {row['index']}")
                        else:
                            self.store.update_status(row['index'], f"Failed: {result}")
                            print(f"❌ فشل معالجة الصف {row['index']}")

                        time.sleep(10) # انتظار بسيط بين الصور

            except Exception as e:
                print(f"❌ خطأ في الدورة: {e}")
            
            time.sleep(self.wait_time)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    orchestrator = MasterOrchestrator()
    orchestrator.run_forever()
