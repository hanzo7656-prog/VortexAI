import os
from dotenv import load_dotenv

load_dotenv()

# API
NOBITEX_API_URL = "https://apiv2.nobitex.ir"
NOBITEX_WS_URL = "ws://ws.nobitex.ir/connection/websocket"
NOBITEX_TOKEN = os.getenv("NOBITEX_TOKEN")
NOBITEX_USERNAME = os.getenv("NOBITEX_USERNAME")
NOBITEX_PASSWORD = os.getenv("NOBITEX_PASSWORD")

# User-Agent
USER_AGENT = os.getenv("USER_AGENT", "TraderBot/MLTraderV1")

# Database
DB_PATH = "db/nobitex.db"

# 20 نماد اولیه
SYMBOLS = [
    "BTCIRT", "ETHIRT", "USDTIRT", "DOGEIRT", "XRPIRT",
    "BNBIRT", "TRXIRT", "ADAIRT", "MATICIRT", "SOLIRT",
    "LTCIRT", "DOTIRT", "AVAXIRT", "SHIBIRT", "LINKIRT",
    "ATOMIRT", "UNIIRT", "FTMIRT", "NEARIRT", "APTIRT"
]

# Timeframes (دقیقه)
BASE_TF = 5
TARGET_TFS = [15, 60, 240, 1440]

# Data retention
MAX_DAYS = 180

# Headers
HEADERS = {
    "Authorization": f"Token {NOBITEX_TOKEN}",
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json"
}
