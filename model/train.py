"""
آموزش مدل XGBoost برای پیش‌بینی قیمت
با قابلیت بازآموزی دوره‌ای
"""

import sqlite3
import pandas as pd
import numpy as np
import pickle
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from feature_engine.gap_detector import GapDetector

# XGBoost
try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    print("⚠️ XGBoost not installed. Run: pip install xgboost scikit-learn")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """آموزش مدل XGBoost"""
    
    def __init__(self, db_path: str = DB_PATH, model_dir: str = "models"):
        self.db_path = db_path
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
    def load_features_from_db(self, symbol: str = None, timeframe: str = "1h", limit: int = 5000) -> pd.DataFrame:
        """بارگذاری ویژگی‌ها از دیتابیس"""
        conn = sqlite3.connect(self.db_path)
        
        if symbol:
            query = """
                SELECT * FROM features
                WHERE timeframe = ? AND symbol = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=[timeframe, symbol, limit])
        else:
            query = """
                SELECT * FROM features
                WHERE timeframe = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=[timeframe, limit])
            
        conn.close()
        
        if df.empty:
            return df
            
        # حذف ردیف‌های بدون هدف
        df = df.dropna(subset=['target'])
        
        return df
    
    def get_feature_columns(self) -> list:
        """لیست ستون‌های ویژگی (بدون هدف و شناسه)"""
        exclude = ['id', 'symbol', 'timeframe', 'timestamp', 'target', 'has_gap']
        all_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'obv', 'bb_upper', 'bb_lower', 'bb_sma',
            'volume_sma_20', 'price_change_1', 'price_change_5',
            'price_change_20', 'daily_high_low_ratio'
        ]
        return all_cols
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, pd.Series]:
        """آماده‌سازی داده برای آموزش"""
        # حذف گپ‌ها
        detector = GapDetector()
        df = detector.filter_no_gap(df)
        
        if df.empty:
            return None, None, None
            
        feature_cols = self.get_feature_columns()
        
        # اطمینان از وجود همه ستون‌ها
        available_cols = [col for col in feature_cols if col in df.columns]
        
        X = df[available_cols].values
        y = df['target'].values
        
        return X, y, df['symbol']
    
    def train_for_symbol(self, symbol: str, timeframe: str = "1h") -> Optional[Dict]:
        """آموزش مدل برای یک نماد خاص"""
        logger.info(f"Training model for {symbol} - {timeframe}")
        
        # بارگذاری داده
        df = self.load_features_from_db(symbol, timeframe)
        
        if df.empty or len(df) < 100:
            logger.warning(f"Not enough data for {symbol}: {len(df)} rows")
            return None
            
        # آماده‌سازی
        X, y, _ = self.prepare_data(df)
        
        if X is None or len(X) < 50:
            return None
            
        # تقسیم داده‌ها
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # آموزش مدل
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0
        )
        
        model.fit(X_train, y_train)
        
        # ارزیابی
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        
        # ذخیره مدل
        model_path = f"{self.model_dir}/{symbol}_{timeframe}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
            
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'mae': mae,
            'mse': mse,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'model_path': model_path,
            'trained_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Model for {symbol}: MAE={mae:.4f}, MSE={mse:.4f}")
        return result
    
    def train_all(self, timeframe: str = "1h", symbols: list = None) -> list:
        """آموزش مدل برای همه نمادها"""
        if symbols is None:
            # دریافت لیست نمادها از دیتابیس
            conn = sqlite3.connect(self.db_path)
            query = "SELECT DISTINCT symbol FROM features WHERE timeframe = ?"
            df = pd.read_sql_query(query, conn, params=[timeframe])
            conn.close()
            symbols = df['symbol'].tolist()
            
        results = []
        for symbol in symbols:
            try:
                result = self.train_for_symbol(symbol, timeframe)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error training {symbol}: {e}")
                
        return results
    
    def load_model(self, symbol: str, timeframe: str = "1h"):
        """بارگذاری مدل ذخیره شده"""
        model_path = f"{self.model_dir}/{symbol}_{timeframe}.pkl"
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                return pickle.load(f)
        return None


class ModelPredictor:
    """پیش‌بینی با مدل آموزش دیده"""
    
    def __init__(self, trainer: ModelTrainer):
        self.trainer = trainer
        self.feature_cols = trainer.get_feature_columns()
        
    def predict(self, symbol: str, features: pd.DataFrame, timeframe: str = "1h") -> Optional[float]:
        """پیش‌بینی برای یک ردیف ویژگی"""
        model = self.trainer.load_model(symbol, timeframe)
        
        if model is None:
            return None
            
        # آماده‌سازی ویژگی‌ها
        available_cols = [col for col in self.feature_cols if col in features.columns]
        X = features[available_cols].values
        
        if len(X) == 0:
            return None
            
        prediction = model.predict(X)
        return prediction[0]
    
    def predict_latest(self, symbol: str, timeframe: str = "1h") -> Optional[Dict]:
        """پیش‌بینی بر اساس آخرین داده"""
        # دریافت آخرین ویژگی‌ها
        df = self.trainer.load_features_from_db(symbol, timeframe, limit=1)
        
        if df.empty:
            return None
            
        prediction = self.predict(symbol, df, timeframe)
        
        if prediction is None:
            return None
            
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'predicted_price': float(prediction),
            'current_price': float(df['close'].iloc[-1]),
            'predicted_change_pct': ((prediction / df['close'].iloc[-1]) - 1) * 100,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    if not XGB_AVAILABLE:
        print("❌ XGBoost not installed. Run: pip install xgboost scikit-learn")
        sys.exit(1)
        
    trainer = ModelTrainer()
    
    # آموزش برای 5 نماد اول با تایم‌فریم 1 ساعت
    results = trainer.train_all(
        timeframe="1h",
        symbols=["BTCIRT", "ETHIRT", "USDTIRT", "DOGEIRT", "XRPIRT"]
    )
    
    print(f"\n📊 Training completed for {len(results)} symbols")
    for r in results:
        print(f"  {r['symbol']}: MAE={r['mae']:.4f}")
        
    # تست پیش‌بینی
    if results:
        predictor = ModelPredictor(trainer)
        for symbol in ["BTCIRT", "ETHIRT"]:
            pred = predictor.predict_latest(symbol)
            if pred:
                print(f"\n🔮 Prediction for {symbol}:")
                print(f"   Current: {pred['current_price']:.2f}")
                print(f"   Predicted: {pred['predicted_price']:.2f}")
                print(f"   Change: {pred['predicted_change_pct']:.2f}%")
