import csv
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class StandardProduct(BaseModel):
    sku: str = "UNKNOWN"
    title: str = ""
    price: float = 0.0
    images: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    completeness_score: float = 0.0

class AuditLogger:
    def __init__(self, log_file="system_audit_log.csv"):
        self.log_file = log_file
        self._setup()
    def _setup(self):
        try:
            with open(self.log_file, mode='x', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow()
        except FileExistsError: pass
    def log_event(self, adapter, action, status, details, score=0.0):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, adapter, action, status, details, score])
        print(f"[{timestamp}][{adapter}] {status.upper()}: {details}")

audit_logger = AuditLogger()

class BaseAdapter:
    def __init__(self, name):
        self.name, self.logger = name, audit_logger
    def _evaluate_quality(self, p):
        score = 0.0
        if p.title: score += 40.0
        if p.price > 0: score += 30.0
        if p.video_url: score += 30.0
        return score
