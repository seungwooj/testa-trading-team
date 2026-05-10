"""
KRX 공개 API로 코스피 전 종목의 업종코드-종목코드 매핑을 생성
  python make_sector_stock_mapping.py

출력: data/sector-stock-mapping.csv
  업종코드, 업종명, 종목코드, 종목명
"""
import sys
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT = BASE_DIR / "data" / "sector-stock-mapping.csv"

# KRX 업종분류현황 API (인증 불필요)
KRX_URL = "http://data.krx.co.kr/comm/bldAttendant/getList.cmd"
HEADERS = {
    "Referer": "http://data.krx.co.kr/contents/MDC/STAT/standard/MDCSTAT03901.cmd",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0",
}

def fetch_sector_mapping(trd_dd: str) -> pd.DataFrame:
    data = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT03901",
        "mktId": "STK",          # KOSPI
        "trdDd": trd_dd,
        "money": "1",
        "csvxls_isNo": "false",
    }
    res = requests.post(KRX_URL, data=data, headers=HEADERS, timeout=15)
    res.raise_for_status()
    body = res.json()

    rows = body.get("output", [])
    if not rows:
        raise ValueError(f"응답에 데이터 없음: {body}")

    df = pd.DataFrame(rows)
    return df

def main():
    trd_dd = datetime.now().strftime("%Y%m%d")
    print(f"KRX 업종분류현황 조회 중... (기준일: {trd_dd})")

    df = fetch_sector_mapping(trd_dd)

    print(f"  원본 컬럼: {df.columns.tolist()}")
    print(f"  행 수: {len(df)}")

    # 컬럼명 정규화 (KRX 응답 컬럼명 → 통일된 이름)
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "iscd" in cl or "code" in cl or "종목코드" in c:
            col_map[c] = "종목코드"
        elif "isnm" in cl or "종목명" in c:
            col_map[c] = "종목명"
        elif "ind_tp_cls_code" in cl or "업종코드" in c or "idxIndCd" in c.lower():
            col_map[c] = "업종코드"
        elif "ind_tp_cls_nm" in cl or "업종명" in c or "idxIndNm" in c.lower():
            col_map[c] = "업종명"

    df = df.rename(columns=col_map)

    # 필요 컬럼만 추출
    need = ["업종코드", "업종명", "종목코드", "종목명"]
    available = [c for c in need if c in df.columns]
    if len(available) < 2:
        print("\n[경고] 컬럼 매핑 실패. 원본 전체를 저장합니다.")
        df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    else:
        df[available].to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"\n저장 완료: {OUTPUT}")
    print(df[available].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
