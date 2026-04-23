import os
from dotenv import load_dotenv

load_dotenv()

# API
NOBITEX_API_URL = "https://apiv2.nobitex.ir"
NOBITEX_WS_URL = "ws://ws.nobitex.ir/connection/websocket"
NOBITEX_TOKEN = os.getenv("NOBITEX_TOKEN")
NOBITEX_USERNAME = os.getenv("NOBITEX_USERNAME")
NOBITEX_PASSWORD = os.getenv("NOBITEX_PASSWORD")

# User-Agent (طبق مستندات نوبیتکس)
USER_AGENT = "TraderBot/MLTraderV1"

# Database
DB_PATH = "db/nobitex.db"

# Symbols (20 نماد اول)
SYMBOLS = [
    "BTCIRT", "ETHIRT", "USDTIRT", "DOGEIRT", "XRPIRT",
    "BNBIRT", "TRXIRT", "ADAIRT", "MATICIRT", "SOLIRT",
    "LTCIRT", "DOTIRT", "AVAXIRT", "SHIBIRT", "LINKIRT",
    "ATOMIRT", "UNIIRT", "FTMIRT", "NEARIRT", "APTIRT"
]

# Timeframes (دقیقه)
BASE_TF = 5  # دقیقه
TARGET_TFS = [15, 60, 240, 1440]  # 15min, 1h, 4h, 1D

# Data retention
MAX_DAYS = 180  # 6 ماه
