import os
from core.orchestrator import MasterOrchestrator
from monitoring.logger import system_log

if __name__ == "__main__":
    system_log.info("BOOTING ENTERPRISE AI BACKEND...")
    port = os.getenv("PORT", "5000")
    orchestrator = MasterOrchestrator()
    orchestrator.run_forever()
