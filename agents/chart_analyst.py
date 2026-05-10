from agents.base_agent import BaseAgent
from tools.kis_market import get_daily_ohlcv
from tools.technical import analyze


class ChartAnalyst(BaseAgent):
    SPEC_FILE = "CHART_ANALYST.md"

    def __init__(self):
        super().__init__("차트 분석가", "차트 분석가 — 이평선 배열, 추세, 눌림목 고점을 분석하는 역할")

    def analyze_stock(self, stock_code: str) -> dict:
        df = get_daily_ohlcv(stock_code, days=80)
        if df.empty or len(df) < 60:
            return {"code": stock_code, "entry_signal": False, "reason": "데이터 부족"}

        result = analyze(df)

        # 전날 종가 기준으로 재확인 (마지막 봉이 오늘 장중이면 전날이 iloc[-2])
        prev_close = df.iloc[-1]["close"]
        prev_above_mid = prev_close > result["ma20"]

        opinion = self.think(
            f"종목 {stock_code} 분석:\n"
            f"- 전날 종가: {prev_close:,.0f}원\n"
            f"- 5일선: {result['ma5']:,.0f} / 20일선: {result['ma20']:,.0f} / 60일선: {result['ma60']:,.0f}\n"
            f"- 정배열(5>20>60): {'✓' if result['ma_aligned'] else '✗'}\n"
            f"- 전날 종가 > 20일선: {'✓' if prev_above_mid else '✗'}\n"
            f"- 60일 우상향 추세: {'✓' if result['rising_trend'] else '✗'}\n"
            f"- 눌림목 이전 고점(돌파 기준): {result['swing_high']:,.0f}원\n"
            f"- 손절가(20일선): {result['ma20']:,.0f}원\n\n"
            f"투자 고려 대상 여부를 판단해주세요."
        )

        # 3가지 조건: 정배열 + 전날종가>20일선 + 우상향 추세
        candidate = result["ma_aligned"] and prev_above_mid and result["rising_trend"]

        return {
            "code": stock_code,
            **result,
            "prev_close": prev_close,
            "prev_above_mid": prev_above_mid,
            "candidate": candidate,
            "opinion": opinion,
        }

    def scan_watchlist(self, watchlist: list[str]) -> list[dict]:
        candidates = []
        for code in watchlist:
            try:
                result = self.analyze_stock(code)
                if result.get("candidate"):
                    candidates.append(result)
            except Exception as e:
                print(f"[ChartAnalyst] {code} 분석 실패: {e}")
        return candidates
