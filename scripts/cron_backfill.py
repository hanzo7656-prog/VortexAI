#!/usr/bin/env python3
"""
کرون جاب برای پر کردن داده‌های گذشته (عقب‌افتادگی)
هر ساعت اجرا شود
"""

import requests
import sqlite3
import time
from datetime import datetime, timedelta
import os
import sys

# اضافه کردن مسیر پروژه
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import NOBITEX_API_URL, HEADERS, SYMBOLS, DB_PATH


def fetch_historical_ohlc(symbol: str, resolution: str, from_ts: int, to_ts: int):
    """دریافت داده تاریخی از نوبیتکس"""
    url = f"{NOBITEX_API_URL}/market/udf/history"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts
    }
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("s") == "ok":
                return data
        return None
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def save_candles_to_db(symbol: str, ohlc_data: dict):
    """ذخیره کندل‌ها در دیتابیس"""
    if not ohlc_data or not ohlc_data.get("t"):
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    timestamps = ohlc_data.get("t", [])
    opens = ohlc_data.get("o", [])
    highs = ohlc_data.get("h", [])
    lows = ohlc_data.get("l", [])
    closes = ohlc_data.get("c", [])
    volumes = ohlc_data.get("v", [])
    
    for i in range(len(timestamps)):
        if i >= len(opens):
            break
            
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO candles
                (symbol, timeframe, timestamp, open, high, low, close, volume, received_at)
                VALUES (?, '5m', ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                timestamps[i],
                str(opens[i]),
                str(highs[i]),
                str(lows[i]),
                str(closes[i]),
                str(volumes[i]),
                int(time.time() * 1000)
            ))
            saved_count += 1
        except Exception as e:
            print(f"Error saving: {e}")
            
    conn.commit()
    conn.close()
    return saved_count


def backfill_all_symbols(hours_back: int = 24):
    """پر کردن داده‌های X ساعت گذشته برای همه نمادها"""
    now = int(time.time())
    from_ts = now - (hours_back * 3600)
    
    total_saved = 0
    
    for symbol in SYMBOLS[:10]:  # شروع با 10 تا
        print(f"Backfilling {symbol}...")
        ohlc = fetch_historical_ohlc(symbol, "5", from_ts, now)
        if ohlc:
            saved = save_candles_to_db(symbol, ohlc)
            total_saved += saved
            print(f"  Saved {saved} candles for {symbol}")
        time.sleep(1)  # احترام به محدودیت نرخ
        
    print(f"✅ Total saved: {total_saved} candles")
    return total_saved


if __name__ == "__main__":
    # پر کردن 24 ساعت گذشته
    backfill_all_symbols(24)
