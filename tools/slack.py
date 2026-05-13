import requests
from config import SLACK_WEBHOOK_URL, MODE


def send(text: str):
    if not SLACK_WEBHOOK_URL:
        return
    requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)


def notify_start(phase: str):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    labels = {
        "pre_open":          "📡 08:00 — 장시작 전 분석 시작",
        "market_open":        "📡 09:00 — 익절 매도 시작",
        "stop_loss_monitor":  "📡 09:05 — 손절 모니터링 시작",
        "entry_monitor":      "📡 10:00 — 고점 돌파 감시 시작",
        "kickoff":            "📡 07:30 — 킥오프 미팅 시작",
        "strategy_debate":    "📡 전략 토론 시작",
    }
    label = labels.get(phase, f"📡 {phase} 시작")
    send(f"*[{mode_tag}] {label}*")


def notify_pre_open(sector: str, candidates: list, profit_targets: list):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"

    if candidates:
        candidate_lines = []
        for c in candidates:
            name = c.get("name", c["code"])
            price = c.get("current_price", c["close"])
            candidate_lines.append(
                f"  • *{name}* (`{c['code']}`)  현재가 {price:,.0f}원\n"
                f"    └ 5일선 {c['ma5']:,.0f} / 20일선 {c['ma20']:,.0f} / 60일선 {c['ma60']:,.0f}\n"
                f"    └ 돌파기준가 {c['swing_high']:,.0f}원  |  손절가 {c['stop_loss']:,.0f}원"
            )
        candidate_text = "\n".join(candidate_lines)
    else:
        candidate_text = "  없음"

    if profit_targets:
        profit_text = "\n".join(
            f"  • {t['name']}({t['code']})  수익률 {t['profit_rate']:+.1f}%  |  현재가 {t['current_price']:,}원"
            for t in profit_targets
        )
    else:
        profit_text = "  없음"

    send(
        f"*[{mode_tag}] ✅ 08:00 — 장시작 전 분석 완료*\n\n"
        f"*선정 섹터:* {sector}\n\n"
        f"*투자 고려 대상:*\n{candidate_text}\n\n"
        f"*익절 대상 (09:00 매도 예정):*\n{profit_text}"
    )


def notify_market_open(sold: list, cash_after: int = 0):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    if not sold:
        send(f"*[{mode_tag}] ✅ 09:00 — 익절 매도 없음*\n현금 잔액: {cash_after:,}원")
        return
    sold_text = "\n".join(f"  • {s['name']}({s['code']}) {s['quantity']}주 @ {s['price']:,}원" for s in sold)
    send(f"*[{mode_tag}] ✅ 09:00 — 익절 매도 완료*\n\n{sold_text}\n\n*현금 잔액: {cash_after:,}원*")


def notify_stop_loss_monitor_end(no_positions: bool = False):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    if no_positions:
        send(f"*[{mode_tag}] ✅ 손절 모니터링 종료*\n보유 종목 없음 — 즉시 종료")
    else:
        send(f"*[{mode_tag}] ✅ 15:30 — 손절 모니터링 종료*")


def notify_buy(code: str, quantity: int, price: int, stop_loss: float):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    send(
        f"*[{mode_tag}] 🟢 매수 체결*\n\n"
        f"종목: {code}\n"
        f"수량: {quantity}주\n"
        f"가격: {price:,}원\n"
        f"손절가: {stop_loss:,.0f}원"
    )


def notify_no_entry():
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    send(f"*[{mode_tag}] ✅ 10:30 — 고점 돌파 종목 없음, 금일 매수 없음*")


def notify_stop_loss(sold: list, cash_after: int = 0):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    lines = "\n".join(
        f"  • {s['name']}({s['code']}) {s['quantity']}주 @ {s['current_price']:,}원  |  손절가: {s['stop_loss']:,}원"
        for s in sold
    )
    send(f"*[{mode_tag}] 🔴 손절 실행*\n\n{lines}\n\n*현금 잔액: {cash_after:,}원*")


def notify_kickoff(lead_close: str, has_mismatch: bool, applied_changes: str = ""):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    summary = lead_close[:4000] + "..." if len(lead_close) > 4000 else lead_close

    if has_mismatch and applied_changes:
        change_block = f"\n\n*자동 반영 결과:*\n{applied_changes}"
    elif has_mismatch:
        change_block = "\n\n⚠️ 불일치 항목이 있으나 자동 반영에 실패했습니다. kickoff_notes.md를 확인하세요."
    else:
        change_block = ""

    send(
        f"*[{mode_tag}] ✅ 킥오프 미팅 완료*{change_block}\n\n"
        f"*팀장 클로징 요약:*\n{summary}"
    )


def notify_strategy_debate(results: list):
    mode_tag = "🟡 모의" if MODE == "mock" else "🔴 실전"
    lines = [f"*[{mode_tag}] ✅ 주말 전략 토론 완료*\n"]
    for i, r in enumerate(results, 1):
        synthesis = r["synthesis"]
        summary = synthesis[:400] + "..." if len(synthesis) > 400 else synthesis
        lines.append(f"*주제 {i}: {r['topic']}*\n{summary}\n")
    send("\n".join(lines))
