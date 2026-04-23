"""
تبدیل داده 5 دقیقه به تایم‌فریم‌های بالاتر
و محاسبه اندیکاتورهای تکنیکال
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH, SYMBOLS, TARGET_TFS
from config.symbols import DEV_SYMBOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureEngine:
    """مهندسی ویژگی‌ها از داده خام 5 دقیقه"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        
    def _get_connection(self):
        """دریافت اتصال به دیتابیس"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def get_candles(self, symbol: str, timeframe: str = "5m", limit: int = 1000) -> pd.DataFrame:
        """دریافت کندل‌ها از دیتابیس"""
        conn = self._get_connection()
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=[symbol, timeframe, limit])
        
        if df.empty:
            return df
            
        # تبدیل به عدد
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # تبدیل timestamp به datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)
        
        return df
    
    def resample_to_higher_tf(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """
        تبدیل تایم‌فریم 5 دقیقه به تایم‌فریم بالاتر
        
        target_tf: '15min', '1h', '4h', '1D'
        """
        if df.empty:
            return df
            
        # تعیین نقشه تبدیل
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # ریسمپل کردن
        resampled = df.resample(target_tf).agg(ohlc_dict)
        
        # حذف ردیف‌های NaN
        resampled = resampled.dropna()
        
        return resampled
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """محاسبه RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series) -> pd.DataFrame:
        """محاسبه MACD"""
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return pd.DataFrame({'macd': macd, 'signal': signal, 'histogram': histogram})
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """محاسبه OBV (On-Balance Volume)"""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20) -> pd.DataFrame:
        """محاسبه باندهای بولینگر"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return pd.DataFrame({'sma': sma, 'upper': upper, 'lower': lower})
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """اضافه کردن همه اندیکاتورها به دیتافریم"""
        if df.empty:
            return df
            
        # قیمت پایانی
        close = df['close']
        
        # RSI
        df['rsi_14'] = self.calculate_rsi(close, 14)
        
        # MACD
        macd_data = self.calculate_macd(close)
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # OBV
        df['obv'] = self.calculate_obv(df)
        
        # باندهای بولینگر
        bb = self.calculate_bollinger_bands(close)
        df['bb_sma'] = bb['sma']
        df['bb_upper'] = bb['upper']
        df['bb_lower'] = bb['lower']
        
        # حجم میانگین متحرک
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        # تغییرات قیمت
        df['price_change_1'] = close.pct_change(1) * 100
        df['price_change_5'] = close.pct_change(5) * 100
        df['price_change_20'] = close.pct_change(20) * 100
        
        # محدوده روزانه
        df['daily_high_low_ratio'] = (df['high'] - df['low']) / df['low'] * 100
        
        return df
    
    def build_features_for_symbol(self, symbol: str, target_tf: str) -> pd.DataFrame:
        """ساخت کامل ویژگی‌ها برای یک نماد و تایم‌فریم مشخص"""
        # دریافت داده 5 دقیقه
        df_5m = self.get_candles(symbol, "5m", limit=5000)
        
        if df_5m.empty:
            logger.warning(f"No data for {symbol}")
            return pd.DataFrame()
        
        # تبدیل به تایم‌فریم هدف
        df = self.resample_to_higher_tf(df_5m, target_tf)
        
        if df.empty:
            return pd.DataFrame()
        
        # اضافه کردن اندیکاتورها
        df = self.add_technical_indicators(df)
        
        # اضافه کردن ستون نماد (برای استفاده به عنوان ویژگی)
        df['symbol'] = symbol
        
        # ستون هدف: قیمت 1 قدم بعد (برای آموزش)
        df['target'] = df['close'].shift(-1)
        
        # حذف ردیف‌های NaN
        df = df.dropna()
        
        return df
    
    def build_all_features(self, symbols: List[str] = None, target_tf: str = "1h") -> pd.DataFrame:
        """ساخت ویژگی‌ها برای همه نمادها"""
        if symbols is None:
            symbols = SYMBOLS[:10]
            
        all_dfs = []
        
        for symbol in symbols:
            logger.info(f"Building features for {symbol} - {target_tf}")
            df = self.build_features_for_symbol(symbol, target_tf)
            if not df.empty:
                all_dfs.append(df)
                
        if not all_dfs:
            return pd.DataFrame()
            
        return pd.concat(all_dfs, ignore_index=False)
    
    def save_features_to_db(self, df: pd.DataFrame, target_tf: str):
        """ذخیره ویژگی‌ها در دیتابیس"""
        if df.empty:
            return
            
        conn = self._get_connection()
        
        # جدول ویژگی‌ها را بساز
        conn.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                rsi_14 REAL,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                obv REAL,
                bb_upper REAL,
                bb_lower REAL,
                bb_sma REAL,
                volume_sma_20 REAL,
                price_change_1 REAL,
                price_change_5 REAL,
                price_change_20 REAL,
                daily_high_low_ratio REAL,
                target REAL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        # ذخیره ردیف به ردیف
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp()) if hasattr(idx, 'timestamp') else 0
            
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO features
                    (symbol, timeframe, timestamp, open, high, low, close, volume,
                     rsi_14, macd, macd_signal, macd_histogram, obv, bb_upper, bb_lower,
                     bb_sma, volume_sma_20, price_change_1, price_change_5, price_change_20,
                     daily_high_low_ratio, target)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['symbol'], target_tf, timestamp,
                    row['open'], row['high'], row['low'], row['close'], row['volume'],
                    row.get('rsi_14'), row.get('macd'), row.get('macd_signal'),
                    row.get('macd_histogram'), row.get('obv'), row.get('bb_upper'),
                    row.get('bb_lower'), row.get('bb_sma'), row.get('volume_sma_20'),
                    row.get('price_change_1'), row.get('price_change_5'), row.get('price_change_20'),
                    row.get('daily_high_low_ratio'), row.get('target')
                ))
            except Exception as e:
                logger.error(f"Error saving row: {e}")
                
        conn.commit()
        logger.info(f"Saved {len(df)} feature rows for timeframe {target_tf}")
        
    def close(self):
        """بستن اتصال دیتابیس"""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    fe = FeatureEngine()
    
    # ساخت ویژگی‌ها برای تایم‌فریم 1 ساعت
    df = fe.build_all_features(symbols=DEV_SYMBOLS, target_tf="1h")
    
    if not df.empty:
        print(f"Features built: {len(df)} rows")
        print(df[['symbol', 'close', 'rsi_14', 'macd']].head())
        
        # ذخیره در دیتابیس
        fe.save_features_to_db(df, "1h")
    else:
        print("No features built. Make sure you have data in candles table.")
    
    fe.close()
