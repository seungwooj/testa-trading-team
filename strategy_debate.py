"""
에이전트 전략 토론 — 매매 로직을 고도화하기 위한 다중 에이전트 토론

실행 방법:
  python strategy_debate.py [mock|real]

결과: data/strategy_notes.md에 저장
토론 주제를 바꾸려면 DEBATE_TOPICS 리스트를 편집하세요.
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from agents.base_agent import BaseAgent, client
from config import BASE_DIR
from tools.slack import notify_strategy_debate, notify_start

OUTPUT = BASE_DIR / "data" / "strategy_notes.md"
GROUNDRULE_PATH = BASE_DIR / "GROUNDRULE.md"

# ── 토론 주제 ────────────────────────────────────────────────────
DEBATE_TOPICS = [
    "현재 전략에서 가장 큰 리스크는 무엇이고, 어떻게 보완할 수 있는가?",
    "섹터 선정 기준(1개월 업종지수 수익률)이 충분한가? 더 나은 기준이 있는가?",
    "진입 조건 3가지(정배열, 전날종가>20일선, 우상향추세)가 실전에서 놓치는 케이스는 무엇인가?",
    "손절/익절 기준을 더 정밀하게 만들 수 있는가?",
]


def load_groundrule() -> str:
    if GROUNDRULE_PATH.exists():
        return GROUNDRULE_PATH.read_text(encoding="utf-8")
    return "(GROUNDRULE.md 파일을 찾을 수 없습니다)"


# ── 토론 에이전트 ─────────────────────────────────────────────────

class DebateAgent(BaseAgent):
    def __init__(self, name: str, role: str, spec_file: Optional[str] = None):
        self.SPEC_FILE = spec_file
        super().__init__(name, role)

    def opening(self, topic: str, groundrule: str) -> str:
        return self.think(
            f"[토론 주제]\n{topic}\n\n"
            f"[현재 매매 전략 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"당신의 전문 영역 관점에서 이 주제에 대한 의견을 제시해주세요. "
            f"현재 전략의 문제점과 개선 방향을 구체적으로 말해주세요."
        )

    def respond(self, topic: str, groundrule: str, others_opinions: str) -> str:
        return self.think(
            f"[토론 주제]\n{topic}\n\n"
            f"[현재 매매 전략 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"[다른 팀원들의 의견]\n{others_opinions}\n\n"
            f"다른 팀원들의 의견을 검토하고, 동의하거나 보완할 점을 말해주세요. "
            f"실행 가능한 구체적인 개선안을 제안해주세요."
        )


class SynthesisLead(BaseAgent):
    SPEC_FILE = "TEAM_LEAD.md"

    def __init__(self):
        super().__init__("팀장", "팀장 — 토론을 종합해 실행 가능한 전략 개선안을 도출하는 역할")

    def synthesize(self, topic: str, groundrule: str, all_opinions: str) -> str:
        return self.think(
            f"[토론 주제]\n{topic}\n\n"
            f"[현재 매매 전략 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"[팀원 전체 의견]\n{all_opinions}\n\n"
            f"위 토론을 종합해서:\n"
            f"1. 핵심 문제점 (1~3가지)\n"
            f"2. 합의된 개선 방향\n"
            f"3. 즉시 실행 가능한 액션 아이템 (구체적인 수치나 코드 변경 포함)\n"
            f"4. GROUNDRULE.md에 반영해야 할 변경사항이 있다면 명시\n"
            f"형식으로 정리해주세요."
        )


# ── 토론 실행 ─────────────────────────────────────────────────────

def run_debate(topic: str, agents: list, lead: SynthesisLead, groundrule: str) -> dict:
    print(f"\n{'─'*60}")
    print(f"주제: {topic}")
    print(f"{'─'*60}")

    # 라운드 1: 각자 의견 제시
    opinions = {}
    for agent in agents:
        print(f"  [{agent.name}] 의견 생성 중...")
        opinions[agent.name] = agent.opening(topic, groundrule)

    # 라운드 2: 다른 의견을 보고 응답
    others_text = "\n\n".join(f"[{name}]\n{op}" for name, op in opinions.items())
    responses = {}
    for agent in agents:
        other_opinions = "\n\n".join(
            f"[{name}]\n{op}" for name, op in opinions.items() if name != agent.name
        )
        print(f"  [{agent.name}] 응답 생성 중...")
        responses[agent.name] = agent.respond(topic, groundrule, other_opinions)

    # 종합: 팀장이 정리
    print(f"  [팀장] 종합 정리 중...")
    all_opinions = (
        "=== 라운드 1: 초기 의견 ===\n" + others_text +
        "\n\n=== 라운드 2: 응답 및 보완 ===\n" +
        "\n\n".join(f"[{name}]\n{r}" for name, r in responses.items())
    )
    synthesis = lead.synthesize(topic, groundrule, all_opinions)

    return {
        "topic": topic,
        "opinions": opinions,
        "responses": responses,
        "synthesis": synthesis,
    }


def save_results(results: list[dict]):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 전략 토론 결과\n",
        f"**생성일시**: {now}\n",
        f"---\n",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"\n## 주제 {i}: {r['topic']}\n")

        lines.append("\n### 팀원 의견\n")
        for name, op in r["opinions"].items():
            lines.append(f"**{name}**\n{op}\n")

        lines.append("\n### 상호 검토\n")
        for name, resp in r["responses"].items():
            lines.append(f"**{name}**\n{resp}\n")

        lines.append("\n### 팀장 종합\n")
        lines.append(r["synthesis"] + "\n")
        lines.append("\n---\n")

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n결과 저장: {OUTPUT}")


def main():
    print("=== 트레이딩 팀 전략 토론 시작 ===\n")

    # GROUNDRULE.md 로드
    groundrule = load_groundrule()
    print(f"[GROUNDRULE.md] {'로드 완료' if GROUNDRULE_PATH.exists() else '파일 없음'}")
    print(f"  → {len(groundrule.splitlines())}줄 로드됨\n")

    agents = [
        DebateAgent("섹터 스카우트", "섹터 분석 전문가 — 어떤 섹터에 투자할지 결정하는 역할", "SECTOR_SCOUT.md"),
        DebateAgent("차트 분석가", "차트 분석 전문가 — 진입 타이밍과 조건을 분석하는 역할", "CHART_ANALYST.md"),
        DebateAgent("리스크 매니저", "리스크 관리 전문가 — 손실 한도와 포지션 크기를 관리하는 역할", "RISK_MANAGER.md"),
        DebateAgent("포트폴리오 매니저", "포트폴리오 관리 전문가 — 전체 자금 배분과 종목 구성을 관리하는 역할", "PORTFOLIO_MANAGER.md"),
    ]
    lead = SynthesisLead()

    results = []
    for topic in DEBATE_TOPICS:
        result = run_debate(topic, agents, lead, groundrule)
        results.append(result)

    save_results(results)
    notify_strategy_debate(results)
    print("\n=== 토론 완료 ===")


if __name__ == "__main__":
    main()
