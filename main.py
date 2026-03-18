import os
import threading
from flask import Flask, jsonify

from core.orchestrator import MasterOrchestrator

app = Flask(__name__)

orchestrator = MasterOrchestrator()

_orchestrator_thread = None
_orchestrator_lock = threading.Lock()
_orchestrator_started = threading.Event()


@app.route("/")
def health():
    is_running = (
        _orchestrator_thread is not None
        and _orchestrator_thread.is_alive()
        and _orchestrator_started.is_set()
    )

    return jsonify({
        "status": "ok",
        "service": "trend-yemen-backend",
        "orchestrator_running": is_running
    })


def start_orchestrator():
    """
    تشغيل الأوركستريتور داخل thread منفصل.
    يتم تعيين started event فقط عند دخول التنفيذ الفعلي.
    """
    print("🚀 Starting Master Orchestrator...")
    _orchestrator_started.set()

    try:
        orchestrator.run()
    except Exception as e:
        print(f"❌ Orchestrator crashed: {e}")
    finally:
        _orchestrator_started.clear()


def start_background_services():
    """
    يمنع التشغيل المزدوج للأوركستريتور.
    إذا كان thread الحالي يعمل بالفعل فلن يتم تشغيله مرة أخرى.
    """
    global _orchestrator_thread

    with _orchestrator_lock:
        if _orchestrator_thread is not None and _orchestrator_thread.is_alive():
            print("⚠️ Orchestrator already running, skipping duplicate start")
            return _orchestrator_thread

        _orchestrator_thread = threading.Thread(
            target=start_orchestrator,
            name="master-orchestrator",
            daemon=True
        )
        _orchestrator_thread.start()
        print("✅ Background services started")
        return _orchestrator_thread


if __name__ == "__main__":
    print("🟢 Starting Trend Yemen Backend...")

    start_background_services()

    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
