#!/usr/bin/env python3
import requests
import sys
import os

MOTHERSHIP_URL = "http://localhost:5001"

def ping_mothership():
    try:
        response = requests.get(f"{MOTHERSHIP_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Mothership is healthy")
            return True
        else:
            print(f"⚠️ Mothership returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Mothership is DOWN! Cannot connect to port 5001")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if not ping_mothership():
        # می‌توانی اینجا به روبیکا/بله اعلان بزنی
        sys.exit(1)
    sys.exit(0)
