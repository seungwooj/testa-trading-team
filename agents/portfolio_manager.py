from agents.base_agent import BaseAgent
from tools.kis_order import buy, get_balance
from config import TRADING_RULES


class PortfolioManager(BaseAgent):
    SPEC_FILE = "PORTFOLIO_MANAGER.md"

    def __init__(self):
        super().__init__("포트폴리오 매니저", "포트폴리오 매니저 — 전체 자금 배분과 최종 매수 실행을 담당하는 역할")

    def execute_buy(self, stock_code: str, quantity: int, price: int) -> dict:
        try:
            result = buy(stock_code, quantity, price)
            print(f"[PortfolioManager] 매수 실행: {stock_code} {quantity}주 @ {price:,}원")
            return {"success": True, "code": stock_code, "quantity": quantity, "price": price, "result": result}
        except Exception as e:
            print(f"[PortfolioManager] 매수 실패 {stock_code}: {e}")
            return {"success": False, "code": stock_code, "error": str(e)}

    def check_capacity(self, current_positions: list, candidates: list[dict]) -> list[dict]:
        """최대 보유 종목 수 제한 내에서 진입 가능 종목 필터링"""
        available_slots = TRADING_RULES["max_positions"] - len(current_positions)
        return candidates[:available_slots]

    def summarize(self, balance: dict, trades_today: list) -> str:
        return self.think(
            f"오늘의 포트폴리오 현황입니다:\n"
            f"- 가용 현금: {balance['cash']:,.0f}원\n"
            f"- 보유 종목 수: {len(balance['positions'])}개\n"
            f"- 오늘 매매: {trades_today}\n\n"
            f"보유 종목:\n"
            + "\n".join(
                f"  {p['name']}({p['code']}): {p['profit_rate']:+.1f}%"
                for p in balance['positions']
            )
            + "\n\n전반적인 포트폴리오 상태를 평가해주세요."
        )
