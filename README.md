# Nobitex ML Trader

سیستم خودکار جمع‌آوری داده، آموزش مدل XGBoost و پیش‌بینی قیمت با استفاده از API نوبیتکس

## نصب سریع

```bash
git clone https://github.com/yourusername/nobitex-ml-trader.git
cd nobitex-ml-trader
python -m venv venv
source venv/bin/activate  # یا venv\Scripts\activate در ویندوز
pip install -r requirements.txt
cp .env.example .env
# توکن خود را در .env وارد کنید


---

### ۶. `.env.example`

```env
# Nobitex credentials
NOBITEX_USERNAME=your_email@example.com
NOBITEX_PASSWORD=your_password
NOBITEX_TOKEN=your_token_from_profile

# Optional
LOG_LEVEL=INFO
MAX_SYMBOLS=20
