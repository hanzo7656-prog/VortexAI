#!/usr/bin/env python3
"""
اجرای Feature Engineering برای همه تایم‌فریم‌ها
این اسکریپت هر 5 دقیقه بعد از داده جدید اجرا شود
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_engine.transformer import FeatureEngine
from feature_engine.gap_detector import GapDetector
from config.symbols import DEV_SYMBOLS


def run_for_timeframes():
    """اجرا برای همه تایم‌فریم‌های هدف"""
    fe = FeatureEngine()
    
    target_tfs = ['15min', '1h', '4h', '1D']
    
    for tf in target_tfs:
        print(f"\n📊 Processing timeframe: {tf}")
        
        try:
            # ساخت ویژگی‌ها
            df = fe.build_all_features(symbols=DEV_SYMBOLS, target_tf=tf)
            
            if not df.empty:
                # تشخیص گپ
                detector = GapDetector()
                df = detector.detect_gaps(df)
                
                bad_rows = df[df['has_gap'] == True]
                if len(bad_rows) > 0:
                    print(f"  ⚠️ Found {len(bad_rows)} rows with gaps (will skip for training)")
                
                # ذخیره در دیتابیس
                fe.save_features_to_db(df, tf)
                print(f"  ✅ Saved {len(df)} rows for {tf}")
            else:
                print(f"  ⚠️ No data for {tf}")
                
        except Exception as e:
            print(f"  ❌ Error for {tf}: {e}")
            
    fe.close()


if __name__ == "__main__":
    print("🚀 Starting Feature Engineering...")
    run_for_timeframes()
    print("✅ Feature Engineering completed")
