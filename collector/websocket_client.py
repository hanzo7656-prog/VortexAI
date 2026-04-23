#!/usr/bin/env python3
"""
WebSocket Client for Nobitex
با قابلیت reconnect خودکار و fallback
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional

import requests
from centrifuge import Centrifuge
from centrifuge.types import SubscriptionPublicationContext

from config.settings import (
    NOBITEX_WS_URL, NOBITEX_TOKEN, SYMBOLS, 
    USER_AGENT, HEADERS, DB_PATH
)
from collector.data_handler import DataHandler

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class NobitexWebSocket:
    """مدیریت اتصال WebSocket به نوبیتکس"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or SYMBOLS[:10]  # شروع با 10 نماد
        self.client = None
        self.subscriptions = {}
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.data_handler = DataHandler(DB_PATH)
        
        # برای fallback
        self.secondary_client = None
        
    def connect(self):
        """اتصال اصلی به WebSocket"""
        logger.info(f"Connecting to {NOBITEX_WS_URL}")
        
        self.client = Centrifuge(NOBITEX_WS_URL, {
            "token": NOBITEX_TOKEN,
            "headers": {
                "User-Agent": USER_AGENT
            }
        })
        
        # رویدادهای اتصال
        self.client.on("connected", self._on_connected)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("error", self._on_error)
        
        self.client.connect()
        
    def _on_connected(self, ctx):
        """وقتی اتصال برقرار شد"""
        logger.info("✅ WebSocket connected successfully")
        self.is_connected = True
        self.reconnect_attempts = 0
        self._subscribe_all()
        
        # به مادرشیپ لاگ بفرست
        self._send_to_mothership("INFO", "WebSocket connected")
        
    def _on_disconnected(self, ctx):
        """وقتی اتصال قطع شد"""
        logger.warning("⚠️ WebSocket disconnected")
        self.is_connected = False
        self._send_to_mothership("WARNING", "WebSocket disconnected")
        
        # تلاش برای reconnect
        self._reconnect()
        
    def _on_error(self, ctx):
        """وقتی خطایی رخ داد"""
        logger.error(f"❌ WebSocket error: {ctx}")
        self._send_to_mothership("ERROR", f"WebSocket error: {ctx}")
        
    def _reconnect(self):
        """تلاش برای reconnect با backoff تصاعدی"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnect attempts reached. Activating fallback...")
            self._activate_fallback()
            return
            
        wait_time = min(2 ** self.reconnect_attempts, 60)  # 1,2,4,8,16,32,60
        self.reconnect_attempts += 1
        
        logger.info(f"Reconnecting in {wait_time} seconds (attempt {self.reconnect_attempts})")
        time.sleep(wait_time)
        self.connect()
        
    def _activate_fallback(self):
        """فعال کردن WebSocket دوم به عنوان fallback"""
        logger.info("🔄 Activating fallback WebSocket...")
        self.secondary_client = Centrifuge(NOBITEX_WS_URL, {
            "token": NOBITEX_TOKEN,
            "headers": {"User-Agent": USER_AGENT}
        })
        self.secondary_client.connect()
        self.client = self.secondary_client
        self.reconnect_attempts = 0
        self._subscribe_all()
        
    def _subscribe_all(self):
        """سابسکرایب به همه کانال‌های مورد نیاز"""
        for symbol in self.symbols:
            # کانال کندل 5 دقیقه‌ای
            channel_5m = f"public:candle-{symbol}-5"
            self._subscribe_to_channel(channel_5m, symbol, "5m")
            
            # کانال آمار بازار
            channel_stats = f"public:market-stats-{symbol}"
            self._subscribe_to_channel(channel_stats, symbol, "stats")
            
        logger.info(f"Subscribed to {len(self.symbols) * 2} channels")
        
    def _subscribe_to_channel(self, channel: str, symbol: str, tf: str):
        """سابسکرایب به یک کانال خاص"""
        try:
            sub = self.client.new_subscription(channel, {"delta": "fossil"})
            
            def on_publication(ctx: SubscriptionPublicationContext):
                self._handle_message(symbol, tf, ctx.data)
            
            sub.on("publication", on_publication)
            sub.subscribe()
            
            self.subscriptions[f"{symbol}_{tf}"] = sub
            logger.debug(f"Subscribed to {channel}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            
    def _handle_message(self, symbol: str, tf: str, data: dict):
        """پردازش پیام دریافتی از WebSocket"""
        try:
            if tf == "5m":
                # داده کندل 5 دقیقه
                record = {
                    "symbol": symbol,
                    "timeframe": "5m",
                    "timestamp": data.get("t"),
                    "open": data.get("o"),
                    "high": data.get("h"),
                    "low": data.get("l"),
                    "close": data.get("c"),
                    "volume": data.get("v"),
                    "received_at": int(time.time() * 1000)
                }
                self.data_handler.save_candle(record)
                logger.debug(f"Saved 5m candle for {symbol}")
                
            elif tf == "stats":
                # داده آمار بازار
                record = {
                    "symbol": symbol,
                    "best_buy": data.get("bestBuy"),
                    "best_sell": data.get("bestSell"),
                    "last_price": data.get("latest"),
                    "day_change": data.get("dayChange"),
                    "volume_24h": data.get("volumeSrc"),
                    "timestamp": int(time.time() * 1000)
                }
                self.data_handler.save_market_stats(record)
                
        except Exception as e:
            logger.error(f"Error handling message for {symbol}: {e}")
            
    def _send_to_mothership(self, level: str, message: str):
        """ارسال لاگ به مادرشیپ"""
        try:
            payload = {
                "module": "websocket_client",
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            # غیربلاکینگ - خطاها نادیده گرفته شوند
            threading.Thread(
                target=self._post_log,
                args=(payload,),
                daemon=True
            ).start()
        except Exception:
            pass
            
    def _post_log(self, payload: dict):
        try:
            requests.post(
                "http://localhost:5001/log",
                json=payload,
                timeout=2
            )
        except Exception:
            pass
            
    def run(self):
        """اجرای main loop"""
        logger.info("Starting Nobitex WebSocket Collector...")
        self.connect()
        
        # نگه داشتن thread اصلی
        try:
            while True:
                time.sleep(1)
                if not self.is_connected and self.reconnect_attempts > self.max_reconnect_attempts:
                    logger.error("Connection lost and fallback failed. Exiting...")
                    break
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            if self.client:
                self.client.disconnect()
                
    def stop(self):
        """توقف graceful"""
        logger.info("Stopping WebSocket client...")
        if self.client:
            self.client.disconnect()


if __name__ == "__main__":
    ws = NobitexWebSocket()
    ws.run()
