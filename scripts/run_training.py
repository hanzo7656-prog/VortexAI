#!/usr/bin/env python3
"""
اسکریپت اجرای آموزش مدل
می‌تواند به صورت دستی یا روزانه با کرون اجرا شود
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.train import ModelTrainer
from config.symbols import DEV_SYMBOLS

def main():
    print("🚀 Starting model training...")
    
    trainer = ModelTrainer()
    
    # آموزش برای همه تایم‌فریم‌ها
    timeframes = ['15min', '1h', '4h', '1D']
    
    for tf in timeframes:
        print(f"\n📊 Training for timeframe: {tf}")
        results = trainer.train_all(
            timeframe=tf,
            symbols=DEV_SYMBOLS
        )
        print(f"  ✅ Trained {len(results)} models for {tf}")
        
    print("\n🎉 Training completed!")

if __name__ == "__main__":
    main()
