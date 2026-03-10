import os
from flask import Flask
from core.orchestrator import MasterOrchestrator
import threading

app = Flask(__name__)

@app.route('/')
def health_check():
    return {"status": "Bot is Active and Safe", "store": "Trend Yemen"}, 200

def run_bot():
    try:
        bot = MasterOrchestrator()
        bot.start_monitoring()
    except Exception as e:
        print(f"Critical Bot Error: {e}")

if __name__ == "__main__":
    # تشغيل محرك البوت في خيط منفصل (Background Thread)
    threading.Thread(target=run_bot, daemon=True).start()
    
    # التشغيل على المنفذ 5000 كما نجح في تقارير Railway الأخيرة
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
