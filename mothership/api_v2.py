"""
سیستم مادر - نسخه کامل با اندپوینت‌های مدل و بازار
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import json
import os
import sys
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH, SYMBOLS
from model.train import ModelTrainer, ModelPredictor

app = FastAPI(title="Nobitex ML Trader API", version="0.2.0")

# فعال کردن CORS برای دسترسی از داشبورد
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مسیر فایل‌های لاگ
LOG_FILE = "logs/mothership.log"
METRICS_FILE = "logs/metrics.json"
HEALTH_STATUS = {"status": "healthy", "last_ping": None, "last_data_update": None}

# مقداردهی اولیه مدل
trainer = ModelTrainer(DB_PATH)
predictor = ModelPredictor(trainer)


class LogEntry(BaseModel):
    module: str
    level: str
    message: str
    timestamp: Optional[datetime] = None


class PredictionResponse(BaseModel):
    symbol: str
    timeframe: str
    predicted_price: float
    current_price: float
    predicted_change_pct: float
    timestamp: str


# ==================== اندپوینت‌های سلامت ====================

@app.get("/health")
def health():
    return {
        "status": HEALTH_STATUS["status"],
        "timestamp": datetime.now().isoformat(),
        "last_data_update": HEALTH_STATUS["last_data_update"]
    }


@app.post("/ping")
def ping():
    HEALTH_STATUS["last_ping"] = datetime.now().isoformat()
    return {"status": "ok"}


# ==================== اندپوینت‌های لاگ ====================

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


@app.delete("/logs")
def clear_logs():
    """پاک‌سازی دستی لاگ"""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        os.makedirs("logs", exist_ok=True)
    return {"status": "cleared"}


# ==================== اندپوینت‌های متریک ====================

@app.get("/metrics")
def get_metrics():
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            return json.load(f)
    return {"metrics": {}}


# ==================== اندپوینت‌های بازار (لحظه‌ای) ====================

@app.get("/market/prices")
def get_current_prices():
    """دریافت آخرین قیمت نمادها از دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    results = []
    for symbol in SYMBOLS[:20]:
        try:
            query = """
                SELECT close, timestamp, day_change, best_buy, best_sell
                FROM candles c
                LEFT JOIN market_stats ms ON c.symbol = ms.symbol
                WHERE c.symbol = ? AND c.timeframe = '5m'
                ORDER BY c.timestamp DESC
                LIMIT 1
            """
            cursor = conn.execute(query, (symbol,))
            row = cursor.fetchone()
            if row:
                results.append({
                    "symbol": symbol,
                    "price": float(row["close"]) if row["close"] else 0,
                    "change_24h": float(row["day_change"]) if row["day_change"] else 0,
                    "best_buy": float(row["best_buy"]) if row["best_buy"] else 0,
                    "best_sell": float(row["best_sell"]) if row["best_sell"] else 0,
                    "last_update": row["timestamp"]
                })
        except Exception as e:
            print(f"Error for {symbol}: {e}")
    
    conn.close()
    return {"prices": results, "count": len(results)}


@app.get("/market/candles")
def get_candles(
    symbol: str,
    timeframe: str = "5m",
    limit: int = 100
):
    """دریافت کندل‌های یک نماد برای چارت"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
        LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=[symbol, timeframe, limit])
    conn.close()
    
    if df.empty:
        return {"candles": []}
    
    # تبدیل به فرمت مناسب برای چارت
    candles = []
    for _, row in df.iterrows():
        candles.append({
            "time": int(row["timestamp"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"])
        })
    
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles}


# ==================== اندپوینت‌های مدل ====================

@app.get("/predict/{symbol}")
def predict_symbol(
    symbol: str,
    timeframe: str = Query("1h", description="تایم‌فریم: 15min, 1h, 4h, 1D")
) -> PredictionResponse:
    """پیش‌بینی قیمت برای یک نماد"""
    try:
        result = predictor.predict_latest(symbol, timeframe)
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"No model or data for {symbol}")
        
        return PredictionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/all")
def predict_all_symbols(
    timeframe: str = Query("1h", description="تایم‌فریم مورد نظر")
):
    """پیش‌بینی برای همه نمادها"""
    results = []
    
    for symbol in SYMBOLS[:20]:
        try:
            pred = predictor.predict_latest(symbol, timeframe)
            if pred:
                results.append(pred)
        except Exception as e:
            print(f"Error predicting {symbol}: {e}")
    
    return {"predictions": results, "count": len(results), "timeframe": timeframe}


@app.get("/models/status")
def get_models_status():
    """وضعیت مدل‌های آموزش دیده"""
    model_dir = "models"
    if not os.path.exists(model_dir):
        return {"models": []}
    
    models = []
    for f in os.listdir(model_dir):
        if f.endswith(".pkl"):
            symbol, tf = f.replace(".pkl", "").split("_")
            models.append({
                "symbol": symbol,
                "timeframe": tf,
                "file": f,
                "size_kb": os.path.getsize(f"{model_dir}/{f}") / 1024
            })
    
    return {"models": models, "count": len(models)}


# ==================== اندپوینت‌های سیستم ====================

@app.get("/system/info")
def system_info():
    """اطلاعات سیستم"""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
        "disk_used_mb": psutil.disk_usage("/").used / (1024 * 1024),
        "disk_free_mb": psutil.disk_usage("/").free / (1024 * 1024)
    }


@app.post("/system/update-data-timestamp")
def update_data_timestamp():
    """بروزرسانی زمان آخرین دریافت داده"""
    HEALTH_STATUS["last_data_update"] = datetime.now().isoformat()
    return {"status": "updated", "timestamp": HEALTH_STATUS["last_data_update"]}


if __name__ == "__main__":
    import uvicorn
    import pandas as pd  # برای اندپوینت candles
    print("🚀 Starting Mothership API v2 on port 5001...")
    uvicorn.run(app, host="0.0.0.0", port=5001)
