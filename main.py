import os
import threading
from flask import Flask
from core.orchestrator import MasterOrchestrator

# 1. إعداد Flask لضمان بقاء السيرفر مستيقظاً في Railway
app = Flask(__name__)

@app.route('/')
def health_check():
    return {"status": "Trend Store Bot is Active 🚀", "service": "Monitoring Sheet"}, 200

def run_bot_logic():
    """تشغيل المحرك الأساسي للفحص"""
    try:
        print("🤖 جاري تشغيل المحرك الأساسي للفحص...")
        bot = MasterOrchestrator()
        # هنا استخدمنا الاسم الصحيح للدالة التي أنشأناها مؤخراً
        bot.run_forever()
    except Exception as e:
        print(f"❌ خطأ حرج في تشغيل البوت: {e}")

if __name__ == "__main__":
    # 2. تشغيل محرك البوت في الخلفية (Thread)
    print("⏳ بدء تشغيل النظام المتكامل...")
    bot_thread = threading.Thread(target=run_bot_logic, daemon=True)
    bot_thread.start()
    
    # 3. تشغيل Flask كواجهة أساسية على المنفذ المطلوب
    port = int(os.getenv("PORT", 5000))
    print(f"🌐 Flask يعمل الآن على المنفذ: {port}")
    app.run(host="0.0.0.0", port=port)
