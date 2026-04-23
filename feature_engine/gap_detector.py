"""
تشخیص گپ در داده
برای جلوگیری از دادن داده گپ‌دار به مدل
"""

import pandas as pd
from datetime import timedelta
from typing import Tuple, Optional

class GapDetector:
    """تشخیص شکاف زمانی در داده"""
    
    def __init__(self, expected_interval_minutes: int = 5):
        self.expected_interval = timedelta(minutes=expected_interval_minutes)
        self.tolerance = timedelta(minutes=expected_interval_minutes * 1.5)  # 1.5 برابر تحمل
        
    def detect_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        تشخیص ردیف‌هایی که گپ دارند
        بازگشت: دیتافریم با ستون new 'has_gap'
        """
        if df.empty or len(df) < 2:
            df['has_gap'] = False
            return df
            
        # محاسبه فاصله زمانی بین ردیف‌ها
        time_diffs = df.index.to_series().diff()
        
        # تشخیص گپ (فاصله بیشتر از حد تحمل)
        df['has_gap'] = time_diffs > self.tolerance
        df['has_gap'] = df['has_gap'].fillna(False)
        
        return df
    
    def filter_no_gap(self, df: pd.DataFrame) -> pd.DataFrame:
        """فقط داده‌های بدون گپ را برگردان"""
        df = self.detect_gaps(df)
        return df[df['has_gap'] == False].copy()
    
    def get_gap_positions(self, df: pd.DataFrame) -> list:
        """لیست موقعیت‌های گپ را برگردان"""
        df = self.detect_gaps(df)
        gap_indices = df[df['has_gap']].index.tolist()
        return gap_indices
    
    def is_continuous(self, df: pd.DataFrame) -> bool:
        """آیا داده پیوسته است؟"""
        df = self.detect_gaps(df)
        return not df['has_gap'].any()


if __name__ == "__main__":
    # تست ساده
    import numpy as np
    
    # ساخت داده نمونه
    dates = pd.date_range('2024-01-01', periods=100, freq='5min')
    df = pd.DataFrame({'close': np.random.randn(100)}, index=dates)
    
    # ایجاد یک گپ مصنوعی (حذف 5 ردیف)
    df = df.drop(dates[30:35])
    
    detector = GapDetector()
    df = detector.detect_gaps(df)
    
    print(f"Data has gaps: {df['has_gap'].any()}")
    print(f"Positions with gaps: {detector.get_gap_positions(df)}")
    print(f"Is continuous: {detector.is_continuous(df)}")
