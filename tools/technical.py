import pandas as pd
from config import TRADING_RULES


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma5"] = df["close"].rolling(TRADING_RULES["short_ma"]).mean()
    df["ma20"] = df["close"].rolling(TRADING_RULES["mid_ma"]).mean()
    df["ma60"] = df["close"].rolling(TRADING_RULES["long_ma"]).mean()
    return df


def is_ma_aligned(df: pd.DataFrame) -> bool:
    """이평선 정배열 확인: 5 > 20 > 60"""
    last = df.iloc[-1]
    return last["ma5"] > last["ma20"] > last["ma60"]


def is_above_mid_ma(df: pd.DataFrame) -> bool:
    """캔들 종가가 20일선 위에서 마감했는지 확인"""
    last = df.iloc[-1]
    return last["close"] > last["ma20"]


def get_mid_ma_price(df: pd.DataFrame) -> float:
    """현재 20일 이평선 가격 (손절가 기준)"""
    return round(df.iloc[-1]["ma20"])


def is_higher_highs_lows(df: pd.DataFrame, lookback: int = 10) -> bool:
    """최근 N봉 기준 고점/저점이 지속 상승하는지 확인"""
    recent = df.tail(lookback)
    highs = recent["high"].tolist()
    lows = recent["low"].tolist()

    rising_highs = all(highs[i] <= highs[i+1] for i in range(len(highs)-3, len(highs)-1))
    rising_lows = all(lows[i] <= lows[i+1] for i in range(len(lows)-3, len(lows)-1))
    return rising_highs and rising_lows


def get_last_swing_high(df: pd.DataFrame, lookback: int = 20) -> float:
    """눌림목 이전 마지막 고점 (진입 돌파 기준가)
    기준: 최근 20일 내, 이후 2거래일 이상 연속 하락이 확인된 가장 최근 고점봉의 고가.
    복수 후보 시 가장 최근 것을 사용. 기준 충족 봉이 없으면 구간 최고가로 fallback.
    """
    recent = df.tail(lookback).reset_index(drop=True)
    n = len(recent)

    # 가장 최근부터 역방향으로 탐색 (최소 2봉 뒤 확인 필요하므로 n-3까지)
    for i in range(n - 3, 0, -1):
        after_1 = recent.iloc[i + 1]["close"]
        after_2 = recent.iloc[i + 2]["close"]
        peak = recent.iloc[i]["close"]
        if after_1 < peak and after_2 < after_1:
            return float(recent.iloc[i]["high"])

    return float(recent["high"].max())


def analyze(df: pd.DataFrame) -> dict:
    """전체 기술적 분석 결과를 하나의 dict로 반환"""
    df = add_moving_averages(df)
    last = df.iloc[-1]

    ma_aligned = is_ma_aligned(df)
    above_mid = is_above_mid_ma(df)
    rising_trend = is_higher_highs_lows(df)
    swing_high = get_last_swing_high(df)
    stop_loss = get_mid_ma_price(df)

    entry_signal = ma_aligned and above_mid and rising_trend and last["close"] >= swing_high

    return {
        "ma5": round(last["ma5"], 0),
        "ma20": round(last["ma20"], 0),
        "ma60": round(last["ma60"], 0),
        "close": last["close"],
        "ma_aligned": ma_aligned,
        "above_mid_ma": above_mid,
        "rising_trend": rising_trend,
        "swing_high": swing_high,
        "stop_loss": stop_loss,
        "entry_signal": entry_signal,
    }
