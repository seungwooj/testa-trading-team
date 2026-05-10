from agents.base_agent import BaseAgent
from tools.kis_order import get_balance, sell
from tools.kis_market import get_current_price
from config import TRADING_RULES


class RiskManager(BaseAgent):
    SPEC_FILE = "RISK_MANAGER.md"

    def __init__(self):
        super().__init__("리스크 매니저", "리스크 관리자 — 손절/익절 기준을 설정하고 기존 포지션을 모니터링하는 역할")

    def calculate_position_size(self, cash: int, entry_price: int, stop_loss: int) -> int:
        """손실 허용 한도 내에서 매수 수량 계산"""
        risk_amount = cash * TRADING_RULES["risk_per_trade"]
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            return 0
        quantity = int(risk_amount / risk_per_share)
        max_by_cash = int((cash * 0.2) / entry_price)  # 현금의 20% 이상 단일 종목 투자 금지
        return min(quantity, max_by_cash)

    def check_stop_loss(self, positions: list[dict], stop_losses: dict) -> list[dict]:
        """보유 종목 중 손절가 도달 여부 확인"""
        triggers = []
        for pos in positions:
            code = pos["code"]
            stop = stop_losses.get(code)
            if stop and pos["current_price"] <= stop:
                triggers.append({**pos, "stop_loss": stop})
        return triggers

    def execute_stop_losses(self, triggers: list[dict]) -> list[str]:
        executed = []
        for pos in triggers:
            try:
                sell(pos["code"], pos["quantity"], pos["current_price"])
                executed.append(pos["code"])
                print(f"[RiskManager] 손절 실행: {pos['code']} @ {pos['current_price']:,}원 (손절가: {pos['stop_loss']:,}원)")
            except Exception as e:
                print(f"[RiskManager] 손절 실패 {pos['code']}: {e}")
        return executed

    def review_candidates(self, candidates: list[dict], cash: int) -> list[dict]:
        """진입 후보 종목에 대해 포지션 크기 계산 및 리스크 의견 추가"""
        reviewed = []
        for c in candidates:
            qty = self.calculate_position_size(cash, int(c["close"]), int(c["stop_loss"]))
            if qty <= 0:
                continue

            opinion = self.think(
                f"종목 {c['code']} 진입 검토:\n"
                f"- 진입가: {c['close']:,.0f}원\n"
                f"- 손절가: {c['stop_loss']:,.0f}원\n"
                f"- 리스크: {((c['close'] - c['stop_loss']) / c['close'] * 100):.1f}%\n"
                f"- 매수 수량: {qty}주\n"
                f"- 투자금액: {int(c['close']) * qty:,.0f}원\n"
                f"- 가용 현금: {cash:,.0f}원\n\n"
                f"이 거래의 리스크가 적절한지 판단해주세요."
            )
            reviewed.append({**c, "quantity": qty, "risk_opinion": opinion})
        return reviewed
