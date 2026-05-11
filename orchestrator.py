"""
testa-trading-team 오케스트레이터

실행 방법:
  python orchestrator.py [mock|real] [pre_close|market_open|entry_monitor]

단계별 스케줄:
  08:00           → pre_close      (섹터/후보 선정, 익절 대상 확인)
  09:00           → market_open    (익절 매도)
  15:00 ~ 15:30   → entry_monitor  (고점 돌파 감시 → 매수)
"""
import sys
import json
import time
from datetime import datetime
from pathlib import Path

from agents.sector_scout import SectorScout
from agents.chart_analyst import ChartAnalyst
from agents.risk_manager import RiskManager
from agents.portfolio_manager import PortfolioManager
from agents.base_agent import BaseAgent
from tools.kis_order import get_balance, sell, buy
from tools.kis_market import get_current_price
from tools.technical import get_mid_ma_price, add_moving_averages
from tools.kis_market import get_daily_ohlcv
from config import BASE_DIR, TRADING_RULES
from tools.slack import notify_pre_close, notify_market_open, notify_buy, notify_no_entry, notify_stop_loss, notify_start, notify_stop_loss_monitor_end

STATE_DIR = BASE_DIR / "data"
CANDIDATES_FILE = STATE_DIR / "candidates.json"
PROFIT_TARGETS_FILE = STATE_DIR / "profit_targets.json"
STOP_LOSS_FILE = STATE_DIR / "stop_losses.json"


# ── 상태 저장/로드 ────────────────────────────────────────────

def save_json(path: Path, data):
    import numpy as np
    class Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, np.integer): return int(o)
            if isinstance(o, np.floating): return float(o)
            if isinstance(o, np.bool_): return bool(o)
            if isinstance(o, np.ndarray): return o.tolist()
            return super().default(o)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=Encoder)


def load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


# ── 팀장 ─────────────────────────────────────────────────────

class TeamLead(BaseAgent):
    SPEC_FILE = "TEAM_LEAD.md"

    def __init__(self):
        super().__init__("팀장", "트레이딩 팀장 — 각 에이전트의 분석을 종합해 최종 매수 결정을 내리는 역할")

    def decide(self, sector_opinion: str, chart_opinion: str, risk_opinion: str) -> str:
        return self.think(
            f"[섹터 분석가]\n{sector_opinion}\n\n"
            f"[차트 분석가]\n{chart_opinion}\n\n"
            f"[리스크 매니저]\n{risk_opinion}\n\n"
            f"위 분석을 종합해 '매수 승인' 또는 '매수 보류'를 결정하고 이유를 간결하게 말해주세요."
        )


# ── 단계 1: 장시작 30분 전 (08:30) ───────────────────────────

def pre_close():
    notify_start("pre_close")
    print(f"\n{'='*50}")
    print(f"[{now()}] 단계1 — 장시작 30분 전 분석 시작")
    print(f"{'='*50}\n")

    sector_scout = SectorScout()
    chart_analyst = ChartAnalyst()
    risk_manager = RiskManager()

    # 1. 섹터 1개 선정
    print("[섹터 선정] 업종지수 1개월 수익률 기준...")
    sector_result = sector_scout.scan()
    print(f"  → 선정 섹터: {sector_result['top_sector']}")
    if sector_result["warning"]:
        print(f"  ⚠ 경고: {sector_result['warning']}")
    print(f"  의견: {sector_result['opinion'][:120]}...\n")

    # 갭 3: 전 섹터 음수 → 신규 매수 보류, 보유 종목 관리만 진행
    if not sector_result["confident"]:
        print("[보류] 섹터 선정 신뢰도 낮음 — 신규 매수 없음. 보유 종목 관리만 진행.\n")
        save_json(CANDIDATES_FILE, {
            "date": today(),
            "sector": sector_result["top_sector"],
            "sector_opinion": sector_result["opinion"],
            "warning": sector_result["warning"],
            "candidates": [],
        })
    else:
        stock_names = sector_result["stock_names"]

        # 2. 후보 종목 선정 (3조건 필터)
        print("[후보 종목 선정] 3조건 필터링...")
        candidates = chart_analyst.scan_watchlist(sector_result["watchlist"])
        for c in candidates:
            c["name"] = stock_names.get(c["code"], c["code"])
            try:
                info = get_current_price(c["code"])
                c["current_price"] = info["price"]
            except Exception:
                c["current_price"] = int(c["close"])
        print(f"  → 투자 고려 대상: {[c['code'] for c in candidates]}\n")
        save_json(CANDIDATES_FILE, {
            "date": today(),
            "sector": sector_result["top_sector"],
            "sector_opinion": sector_result["opinion"],
            "warning": sector_result.get("warning", ""),
            "candidates": candidates,
        })
        candidates = candidates  # 아래 보유 종목 확인 단계에서도 사용

    # 3. 현재 보유 종목 상태 확인 + 익절 대상 선정
    print("[보유 종목 확인] 익절 대상 선정...")
    try:
        balance = get_balance()
    except Exception as e:
        print(f"  잔고 조회 실패 (장 외 시간): {e}")
        balance = {"cash": 0, "positions": []}
    stop_losses = load_json(STOP_LOSS_FILE, {})
    profit_targets = []

    for pos in balance["positions"]:
        code = pos["code"]
        df = get_daily_ohlcv(code, days=80)
        if df.empty:
            continue
        df = add_moving_averages(df)
        ma20 = get_mid_ma_price(df)
        stop_loss = stop_losses.get(code, 0)
        is_profit_target = pos["current_price"] < ma20

        print(f"  {pos['name']}({code}): "
              f"매수가 {pos['avg_price']:,.0f} / 현재 {pos['current_price']:,.0f} / "
              f"수익률 {pos['profit_rate']:+.1f}% / 손절가 {stop_loss:,.0f} / "
              f"익절대상 {'✓' if is_profit_target else '-'}")

        if is_profit_target:
            profit_targets.append({**pos, "ma20": ma20})

    save_json(PROFIT_TARGETS_FILE, {"date": today(), "targets": profit_targets})
    print(f"\n  → 익절 대상: {[t['code'] for t in profit_targets]}")
    print(f"\n[완료] 09:00 익절 매도, 14:30~15:30 고점 돌파 시 매수 예정\n")
    notify_pre_close(sector_result["top_sector"], candidates, profit_targets)


# ── 단계 2: 장시작 (09:00) ───────────────────────────────────

def market_open():
    notify_start("market_open")
    print(f"\n{'='*50}")
    print(f"[{now()}] 단계2 — 장시작 익절 매도")
    print(f"{'='*50}\n")

    state = load_json(PROFIT_TARGETS_FILE, {"targets": []})
    targets = state.get("targets", [])

    if not targets:
        print("  익절 대상 없음\n")
        try:
            balance_now = get_balance()
            cash_now = balance_now["cash"]
        except Exception:
            cash_now = 0
        notify_market_open([], cash_now)
        return

    stop_losses = load_json(STOP_LOSS_FILE, {})

    sold_results = []
    for t in targets:
        try:
            current = get_current_price(t["code"])
            sell(t["code"], t["quantity"], current["price"])
            stop_losses.pop(t["code"], None)
            sold_results.append({**t, "price": current["price"]})
            print(f"  익절 매도: {t['name']}({t['code']}) {t['quantity']}주 @ {current['price']:,}원")
        except Exception as e:
            print(f"  익절 매도 실패 {t['code']}: {e}")

    save_json(STOP_LOSS_FILE, stop_losses)
    save_json(PROFIT_TARGETS_FILE, {"date": today(), "targets": []})

    # 갭 2: 매도 후 현금 잔액 조회 → 슬랙에 포함 (14:30 포지션 계산 기준)
    try:
        balance_after = get_balance()
        cash_after = balance_after["cash"]
    except Exception:
        cash_after = 0
    notify_market_open(sold_results, cash_after)
    print()


# ── 단계 2-5: 09:05~15:30 손절 모니터링 ─────────────────────

def stop_loss_monitor():
    notify_start("stop_loss_monitor")
    print(f"\n{'='*50}")
    print(f"[{now()}] 손절 모니터링 시작 (15:30까지)")
    print(f"{'='*50}\n")

    stop_losses = load_json(STOP_LOSS_FILE, {})
    if not stop_losses:
        print("  보유 종목 없음 — 모니터링 종료\n")
        notify_stop_loss_monitor_end(no_positions=True)
        return

    risk_manager = RiskManager()
    print(f"  모니터링 종목: {list(stop_losses.keys())}\n")

    while datetime.now().strftime("%H%M") < "1530":
        try:
            balance = get_balance()
        except Exception as e:
            print(f"  [{now()}] 잔고 조회 실패: {e}")
            time.sleep(60)
            continue

        stop_triggered = [
            {**pos, "stop_loss": stop_losses[pos["code"]]}
            for pos in balance["positions"]
            if pos["code"] in stop_losses and pos["current_price"] <= stop_losses[pos["code"]]
        ]

        if stop_triggered:
            executed_codes = risk_manager.execute_stop_losses(stop_triggered)
            for pos in stop_triggered:
                if pos["code"] in executed_codes:
                    stop_losses.pop(pos["code"], None)
            save_json(STOP_LOSS_FILE, stop_losses)
            executed = [p for p in stop_triggered if p["code"] in executed_codes]
            if executed:
                try:
                    cash_after = get_balance()["cash"]
                except Exception:
                    cash_after = 0
                notify_stop_loss(executed, cash_after)

        if datetime.now().strftime("%H%M") >= "1530":
            break
        time.sleep(60)

    notify_stop_loss_monitor_end()
    print(f"  [{now()}] 손절 모니터링 종료\n")


# ── 단계 3: 14:30~15:30 고점 돌파 감시 → 매수 ────────────────

def entry_monitor():
    notify_start("entry_monitor")
    print(f"\n{'='*50}")
    print(f"[{now()}] 단계3 — 고점 돌파 감시 시작 (15:00~15:30)")
    print(f"{'='*50}\n")

    state = load_json(CANDIDATES_FILE, {"candidates": []})
    candidates = state.get("candidates", [])

    if not candidates:
        print("  투자 고려 대상 없음\n")
        return

    risk_manager = RiskManager()
    portfolio_manager = PortfolioManager()
    team_lead = TeamLead()
    sector_opinion = state.get("sector_opinion", "")
    stop_losses = load_json(STOP_LOSS_FILE, {})
    bought = set()

    print(f"  감시 종목: {[c['code'] for c in candidates]}\n")

    while datetime.now().strftime("%H%M") <= "1530":
        balance = get_balance()
        current_codes = {p["code"] for p in balance["positions"]}

        # 갭 4: 동시 돌파 대비 — 리스크 비율 낮은 순(손절가와 진입가 간격이 좁은 순)으로 우선 처리
        def risk_ratio(c):
            swing = c.get("swing_high", 0)
            ma20 = c.get("ma20", 0)
            if swing and ma20:
                return (swing - ma20) / swing
            return 1.0

        sorted_candidates = sorted(
            [c for c in candidates if c["code"] not in bought and c["code"] not in current_codes],
            key=risk_ratio
        )

        for c in sorted_candidates:
            code = c["code"]

            try:
                price_data = get_current_price(code)
                current_price = price_data["price"]
                swing_high = c["swing_high"]

                if current_price >= swing_high:
                    print(f"  [{now()}] {code} 고점 돌파! 현재가 {current_price:,} >= 고점 {swing_high:,.0f}")

                    reviewed = risk_manager.review_candidates([{**c, "close": current_price}], balance["cash"])
                    if not reviewed:
                        print(f"  → 리스크 기준 미달, 건너뜀")
                        continue

                    decision = team_lead.decide(
                        sector_opinion=sector_opinion,
                        chart_opinion=c["opinion"],
                        risk_opinion=reviewed[0]["risk_opinion"],
                    )
                    print(f"  팀장 결정: {decision[:100]}...")

                    if "매수 승인" in decision:
                        qty = reviewed[0]["quantity"]
                        result = buy(code, qty, current_price)
                        stop_price = c["ma20"]
                        stop_losses[code] = stop_price
                        save_json(STOP_LOSS_FILE, stop_losses)
                        bought.add(code)
                        notify_buy(code, qty, current_price, stop_price)
                        print(f"  ✓ 매수 완료: {code} {qty}주 @ {current_price:,}원 | 손절가: {stop_price:,.0f}원\n")

            except Exception as e:
                print(f"  {code} 처리 실패: {e}")

        if datetime.now().strftime("%H%M") > "1530":
            break
        time.sleep(60)

    if not bought:
        notify_no_entry()
    print(f"  [{now()}] 감시 종료. 금일 매수: {list(bought)}\n")


# ── 유틸 ─────────────────────────────────────────────────────

def now():
    return datetime.now().strftime("%H:%M:%S")

def today():
    return datetime.now().strftime("%Y-%m-%d")


# ── 메인 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    phase = sys.argv[2] if len(sys.argv) > 2 else "pre_close"

    if phase == "pre_close":
        pre_close()
    elif phase == "market_open":
        market_open()
    elif phase == "stop_loss_monitor":
        stop_loss_monitor()
    elif phase == "entry_monitor":
        entry_monitor()
    else:
        print(f"알 수 없는 단계: {phase}")
        print("사용법: python orchestrator.py [mock|real] [pre_close|market_open|stop_loss_monitor|entry_monitor]")
