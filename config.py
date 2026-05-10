import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
MODE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("mock", "real") else "mock"
load_dotenv(BASE_DIR / f".env.{MODE}", override=True)

KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")
KIS_ACCOUNT_PROD_CODE = os.getenv("KIS_ACCOUNT_PROD_CODE", "01")
KIS_TRADE_URL = os.getenv("KIS_TRADE_URL")
KIS_WS_URL = os.getenv("KIS_WS_URL")
KIS_MARKET_URL = KIS_TRADE_URL  # 시세도 동일 URL 사용

KIS_TR_BUY = os.getenv("KIS_TR_BUY")
KIS_TR_SELL = os.getenv("KIS_TR_SELL")
KIS_TR_BALANCE = os.getenv("KIS_TR_BALANCE")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

TRADING_RULES = {
    "short_ma": 5,
    "mid_ma": 20,
    "long_ma": 60,
    "max_positions": 5,
    "risk_per_trade": 0.02,
}
