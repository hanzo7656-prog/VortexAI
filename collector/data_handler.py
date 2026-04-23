"""مدیریت ذخیره‌سازی داده در SQLite"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataHandler:
    """مدیریت دیتابیس SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """ایجاد جداول مورد نیاز"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول کندل‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open TEXT,
                high TEXT,
                low TEXT,
                close TEXT,
                volume TEXT,
                received_at INTEGER,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        # جدول آمار بازار
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                best_buy TEXT,
                best_sell TEXT,
                last_price TEXT,
                day_change TEXT,
                volume_24h TEXT,
                timestamp INTEGER,
                UNIQUE(symbol, timestamp)
            )
        """)
        
        # جدول لاگ‌های داخلی
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT,
                status TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
        
    def save_candle(self, record: Dict):
        """ذخیره کندل"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO candles 
                (symbol, timeframe, timestamp, open, high, low, close, volume, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["symbol"],
                record["timeframe"],
                record["timestamp"],
                record.get("open"),
                record.get("high"),
                record.get("low"),
                record.get("close"),
                record.get("volume"),
                record.get("received_at")
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save candle: {e}")
            
    def save_market_stats(self, record: Dict):
        """ذخیره آمار بازار"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO market_stats
                (symbol, best_buy, best_sell, last_price, day_change, volume_24h, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record["symbol"],
                record.get("best_buy"),
                record.get("best_sell"),
                record.get("last_price"),
                record.get("day_change"),
                record.get("volume_24h"),
                record.get("timestamp")
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save market stats: {e}")
            
    def get_last_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """دریافت آخرین کندل‌ها"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM candles
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
