import requests
from tools.kis_auth import get_trade_headers
from config import KIS_TRADE_URL, KIS_ACCOUNT_NO, KIS_ACCOUNT_PROD_CODE, KIS_TR_BUY, KIS_TR_SELL, KIS_TR_BALANCE


def buy(stock_code: str, quantity: int, price: int) -> dict:
    headers = get_trade_headers(KIS_TR_BUY)
    body = {
        "CANO": KIS_ACCOUNT_NO,
        "ACNT_PRDT_CD": KIS_ACCOUNT_PROD_CODE,
        "PDNO": stock_code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
    }
    res = requests.post(f"{KIS_TRADE_URL}/uapi/domestic-stock/v1/trading/order-cash", headers=headers, json=body)
    res.raise_for_status()
    return res.json()


def sell(stock_code: str, quantity: int, price: int) -> dict:
    headers = get_trade_headers(KIS_TR_SELL)
    body = {
        "CANO": KIS_ACCOUNT_NO,
        "ACNT_PRDT_CD": KIS_ACCOUNT_PROD_CODE,
        "PDNO": stock_code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
    }
    res = requests.post(f"{KIS_TRADE_URL}/uapi/domestic-stock/v1/trading/order-cash", headers=headers, json=body)
    res.raise_for_status()
    return res.json()


def get_balance() -> dict:
    headers = get_trade_headers(KIS_TR_BALANCE)
    params = {
        "CANO": KIS_ACCOUNT_NO,
        "ACNT_PRDT_CD": KIS_ACCOUNT_PROD_CODE,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    res = requests.get(f"{KIS_TRADE_URL}/uapi/domestic-stock/v1/trading/inquire-balance", headers=headers, params=params)
    res.raise_for_status()
    data = res.json()
    return {
        "cash": int(data["output2"][0].get("dnca_tot_amt", 0)),
        "positions": [
            {
                "code": p["pdno"],
                "name": p["prdt_name"],
                "quantity": int(p["hldg_qty"]),
                "avg_price": float(p["pchs_avg_pric"]),
                "current_price": int(p["prpr"]),
                "profit_rate": float(p["evlu_pfls_rt"]),
            }
            for p in data.get("output1", [])
        ],
    }
