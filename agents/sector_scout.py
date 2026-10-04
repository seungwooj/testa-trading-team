import json
from agents.base_agent import BaseAgent
from tools.kis_market import get_index_ohlcv
from config import BASE_DIR

SECTORS_FILE = BASE_DIR / "data" / "sectors.json"


def load_sectors() -> dict:
    with open(SECTORS_FILE) as f:
        return json.load(f)


class SectorScout(BaseAgent):
    SPEC_FILE = "SECTOR_SCOUT.md"

    def __init__(self):
        super().__init__("섹터 스카우트", "섹터 분석가 — 최근 1개월 업종지수 수익률 기준으로 자금이 가장 많이 몰린 상위 3개 섹터를 선정하는 역할")

    def _index_1m_return(self, index_code: str) -> float:
        """업종지수의 최근 1개월 수익률 (%)"""
        try:
            df = get_index_ohlcv(index_code, days=25)
            if len(df) < 2:
                return 0.0
            oldest = df.iloc[0]["close"]
            latest = df.iloc[-1]["close"]
            if not oldest:
                return 0.0
            return round((latest - oldest) / oldest * 100, 2)
        except Exception:
            return 0.0

    def _check_confidence(self, returns: dict) -> tuple:
        """섹터 선정 신뢰도 확인. (confidence: bool, warning: str)"""
        sorted_returns = sorted(returns.values(), reverse=True)
        all_negative = all(r <= 0 for r in sorted_returns)
        top_gap = sorted_returns[0] - sorted_returns[1] if len(sorted_returns) >= 2 else 999

        if all_negative:
            return False, "전 섹터 수익률 음수 — 시장 전반 약세. 당일 신규 매수 보류 권장."
        if top_gap < 1.0:
            return True, f"1위·2위 섹터 수익률 차이 {top_gap:.2f}%p 미만 — 추세 불분명. 진입 시 주의."
        return True, ""

    def scan(self) -> dict:
        sectors = load_sectors()

        sector_returns = {}
        for name, data in sectors.items():
            index_code = data.get("index_code", "")
            sector_returns[name] = self._index_1m_return(index_code) if index_code else 0.0

        sorted_sectors = sorted(sector_returns.items(), key=lambda x: -x[1])
        confident, warning = self._check_confidence(sector_returns)

        top_3 = sorted_sectors[:3]
        top_sectors = []
        for name, ret in top_3:
            stocks = sectors[name]["stocks"]
            top_sectors.append({
                "name": name,
                "return": ret,
                "watchlist": [s["code"] for s in stocks],
                "stock_names": {s["code"]: s["name"] for s in stocks},
            })

        top_sector = top_3[0][0]

        prompt = (
            f"최근 1개월 업종지수 수익률입니다:\n"
            + "\n".join(f"- {s}: {r:+.2f}%" for s, r in sorted_sectors)
        )
        if warning:
            prompt += f"\n\n[주의] {warning}"
        prompt += (
            f"\n\n상위 3개 섹터({', '.join(s['name'] for s in top_sectors)})를 선정한 이유와 "
            f"시장 흐름을 간결하게 설명해주세요."
        )

        opinion = self.think(prompt)

        return {
            "returns": sector_returns,
            "top_sector": top_sector,
            "top_sectors": top_sectors,
            "opinion": opinion,
            "confident": confident,
            "warning": warning,
        }
