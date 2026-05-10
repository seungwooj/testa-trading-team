import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from tools.kis_auth import get_market_headers as get_headers
from config import KIS_MARKET_URL


def get_daily_ohlcv(stock_code: str, days: int = 80) -> pd.DataFrame:
    """일봉 데이터 조회 — 55일 캘린더 단위로 나눠 요청, days 거래일 확보"""
    all_rows = []
    end_date = datetime.today()

    while len(all_rows) < days:
        start_date = end_date - timedelta(days=55)
        headers = get_headers("FHKST01010400")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        }
        res = requests.get(
            f"{KIS_MARKET_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            headers=headers,
            params=params,
        )
        if not res.ok:
            break
        rows = res.json().get("output", [])
        if not rows:
            break
        all_rows = rows + all_rows
        end_date = start_date - timedelta(days=1)
        time.sleep(0.05)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows).rename(columns={
        "stck_bsop_date": "date",
        "stck_oprc": "open",
        "stck_hgpr": "high",
        "stck_lwpr": "low",
        "stck_clpr": "close",
        "acml_vol": "volume",
    })
    df[["open", "high", "low", "close", "volume"]] = (
        df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
    )
    return df.sort_values("date").tail(days).reset_index(drop=True)


def get_current_price(stock_code: str) -> dict:
    """현재가 조회"""
    headers = get_headers("FHKST01010100")
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    res = requests.get(
        f"{KIS_MARKET_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers,
        params=params,
    )
    res.raise_for_status()
    output = res.json().get("output", {})
    return {
        "code": stock_code,
        "name": output.get("hts_kor_isnm", stock_code),
        "price": int(output.get("stck_prpr", 0)),
        "change_rate": float(output.get("prdy_ctrt", 0)),
        "volume": int(output.get("acml_vol", 0)),
        "trade_value": float(output.get("acml_tr_pbmn", 0)),
    }


def get_index_ohlcv(index_code: str, days: int = 30) -> pd.DataFrame:
    """업종지수 일봉 조회 — days 거래일 확보"""
    all_rows = []
    end_date = datetime.today()

    while len(all_rows) < days:
        start_date = end_date - timedelta(days=55)
        headers = get_headers("FHKUP03500100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
        }
        res = requests.get(
            f"{KIS_MARKET_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
            headers=headers,
            params=params,
        )
        if not res.ok:
            break
        rows = res.json().get("output2", [])
        if not rows:
            break
        all_rows = rows + all_rows
        end_date = start_date - timedelta(days=1)
        time.sleep(0.05)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows).rename(columns={
        "stck_bsop_date": "date",
        "bstp_nmix_oprc": "open",
        "bstp_nmix_hgpr": "high",
        "bstp_nmix_lwpr": "low",
        "bstp_nmix_prpr": "close",
        "acml_vol": "volume",
    })
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").tail(days).reset_index(drop=True)
