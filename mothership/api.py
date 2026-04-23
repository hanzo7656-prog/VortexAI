from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
import json
import os
from typing import Optional, List

app = FastAPI(title="Mothership Monitor", version="0.1.0")

# مسیر فایل‌های لاگ
LOG_FILE = "logs/mothership.log"
METRICS_FILE = "logs/metrics.json"
HEALTH_STATUS = {"status": "healthy", "last_ping": None}

class LogEntry(BaseModel):
    module: str
    level: str  # INFO, WARNING, ERROR
    message: str
    timestamp: Optional[datetime] = None

@app.get("/health")
def health():
    return {"status": HEALTH_STATUS["status"], "timestamp": datetime.now().isoformat()}

@app.post("/ping")
def ping():
    from datetime import datetime
    HEALTH_STATUS["last_ping"] = datetime.now().isoformat()
    return {"status": "ok"}

@app.post("/log")
def receive_log(log: LogEntry):
    if log.timestamp is None:
        log.timestamp = datetime.now()
    
    log_line = f"{log.timestamp.isoformat()} | {log.module} | {log.level} | {log.message}\n"
    
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_line)
    
    return {"status": "logged"}

@app.get("/logs")
def get_logs(lines: int = 100):
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    
    with open(LOG_FILE, "r") as f:
        all_lines = f.readlines()
    
    return {"logs": all_lines[-lines:]}

@app.get("/metrics")
def get_metrics():
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            return json.load(f)
    return {"metrics": {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
