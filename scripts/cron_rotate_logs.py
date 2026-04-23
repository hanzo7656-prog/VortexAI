#!/usr/bin/env python3
import os
import glob
from datetime import datetime, timedelta

LOG_DIR = "logs"
KEEP_HOURS = 24

def rotate_logs():
    now = datetime.now()
    cutoff = now - timedelta(hours=KEEP_HOURS)
    
    if not os.path.exists(LOG_DIR):
        print("No logs directory")
        return
    
    for log_file in glob.glob(f"{LOG_DIR}/*.log"):
        mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
        if mtime < cutoff:
            print(f"Removing old log: {log_file}")
            os.remove(log_file)
    
    # همچنین فایل‌های لاگ خالی را پاک کن
    for log_file in glob.glob(f"{LOG_DIR}/*.log"):
        if os.path.getsize(log_file) == 0:
            os.remove(log_file)

if __name__ == "__main__":
    rotate_logs()
