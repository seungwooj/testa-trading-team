import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_TRADE_URL, KIS_MARKET_URL, MODE, BASE_DIR

_TOKEN_FILE = BASE_DIR / f".token.{MODE}.json"


def _load_cached_token() -> dict:
    if os.path.exists(_TOKEN_FILE):
        with open(_TOKEN_FILE) as f:
            return json.load(f)
    return {}


def _save_token(token: str, expires_at: datetime):
    with open(_TOKEN_FILE, "w") as f:
        json.dump({"token": token, "expires_at": expires_at.isoformat()}, f)


def get_access_token(base_url: str) -> str:
    cached = _load_cached_token()
    if cached.get("token") and datetime.fromisoformat(cached["expires_at"]) > datetime.now():
        return cached["token"]

    res = requests.post(
        f"{base_url}/oauth2/tokenP",
        json={"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET},
    )
    res.raise_for_status()
    data = res.json()
    expires_at = datetime.now() + timedelta(seconds=int(data["expires_in"]) - 60)
    _save_token(data["access_token"], expires_at)
    return data["access_token"]


def get_trade_headers(tr_id: str) -> dict:
    return {
        "authorization": f"Bearer {get_access_token(KIS_TRADE_URL)}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P",
        "content-type": "application/json",
    }


def get_market_headers(tr_id: str) -> dict:
    return {
        "authorization": f"Bearer {get_access_token(KIS_MARKET_URL)}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P",
        "content-type": "application/json",
    }
