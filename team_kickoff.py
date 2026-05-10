"""
팀 킥오프 미팅 — GROUNDRULE.md를 읽어 에이전트들이 최신 전략을 숙지하고 각자의 역할을 확인

실행 방법:
  python team_kickoff.py [mock|real]

결과: data/kickoff_notes.md에 저장
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from agents.base_agent import BaseAgent
from config import BASE_DIR
from tools.slack import notify_kickoff, notify_start

OUTPUT = BASE_DIR / "data" / "kickoff_notes.md"
GROUNDRULE_PATH = BASE_DIR / "GROUNDRULE.md"


def load_groundrule() -> str:
    if GROUNDRULE_PATH.exists():
        return GROUNDRULE_PATH.read_text(encoding="utf-8")
    return "(GROUNDRULE.md 파일을 찾을 수 없습니다)"


class KickoffAgent(BaseAgent):
    def __init__(self, name: str, role: str, spec_file: Optional[str] = None):
        self.SPEC_FILE = spec_file
        super().__init__(name, role)

    def verify_groundrule(self, groundrule: str) -> str:
        """GROUNDRULE.md를 읽고, 자신의 역할과 판단 기준이 최신 전략과 일치하는지 확인"""
        return self.think(
            f"[최신 전략 지침 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"위 GROUNDRULE.md를 읽었습니다. 당신({self.name})의 역할 관점에서:\n"
            f"1. 내가 담당하는 항목과 기준이 무엇인지 GROUNDRULE.md 기준으로 정리해주세요\n"
            f"2. 내 판단 지침(.md 파일)과 GROUNDRULE.md 사이에 불일치하거나 모호한 부분이 있다면 지적해주세요\n"
            f"3. 이번 주 운영 시 특별히 주의해야 할 사항이 있다면 말해주세요"
        )

    def confirm_understanding(self, groundrule: str, others_summaries: str) -> str:
        return self.think(
            f"[최신 전략 지침 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"[다른 팀원들의 역할 정리]\n{others_summaries}\n\n"
            f"팀 전체 흐름을 보고 아래를 답해주세요:\n"
            f"1. 내 역할과 다른 팀원의 역할이 잘 연결되어 있는가?\n"
            f"2. GROUNDRULE.md 기준으로 현재 흐름에서 빠졌거나 모호한 부분이 있는가?\n"
            f"3. 실제 운영 시 내가 특히 주의해야 할 케이스는?"
        )


class KickoffLead(BaseAgent):
    SPEC_FILE = "TEAM_LEAD.md"

    def __init__(self):
        super().__init__("팀장", "트레이딩 팀장 — 킥오프 미팅을 주재하고 팀 전체 흐름을 점검하는 역할")

    def open_meeting(self, groundrule: str) -> str:
        return self.think(
            f"[최신 전략 지침 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"오늘 팀 킥오프 미팅을 시작합니다.\n"
            f"GROUNDRULE.md를 검토하고, 팀장으로서 다음을 말해주세요:\n"
            f"1. 이 전략의 핵심 철학 (왜 이렇게 운영하는가)\n"
            f"2. 각 단계에서 팀 전체가 반드시 지켜야 할 원칙\n"
            f"3. 오늘 팀원들에게 특별히 당부하고 싶은 사항"
        )

    def close_meeting(self, groundrule: str, all_summaries: str) -> str:
        return self.think(
            f"[최신 전략 지침 — GROUNDRULE.md]\n{groundrule}\n\n"
            f"[팀원 전체 역할 검토 결과]\n{all_summaries}\n\n"
            f"킥오프 미팅을 마무리합니다. 다음을 정리해주세요:\n"
            f"1. GROUNDRULE.md와 각 에이전트 .md 파일 사이에 업데이트가 필요한 항목 (있다면 구체적으로)\n"
            f"2. 팀원들이 공통으로 지적한 주의사항 또는 개선점\n"
            f"3. 오늘 실제 운영 시작 전 확인해야 할 체크리스트"
        )


def save_results(groundrule_loaded: bool, lead_open: str, verifications: dict, confirmations: dict, lead_close: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 팀 킥오프 미팅 기록\n",
        f"**일시**: {now}\n",
        f"**GROUNDRULE.md 로드**: {'성공' if groundrule_loaded else '실패 (파일 없음)'}\n",
        f"---\n",
        f"\n## 팀장 오프닝\n",
        lead_open,
        f"\n---\n",
        f"\n## GROUNDRULE.md 기반 역할 확인\n",
    ]

    for name, v in verifications.items():
        lines.append(f"\n### {name}\n")
        lines.append(v)

    lines.append(f"\n---\n")
    lines.append(f"\n## 상호 확인 및 보완\n")

    for name, conf in confirmations.items():
        lines.append(f"\n### {name}\n")
        lines.append(conf)

    lines.append(f"\n---\n")
    lines.append(f"\n## 팀장 클로징\n")
    lines.append(lead_close)

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main():
    notify_start("kickoff")
    print("=" * 60)
    print("  트레이딩 팀 킥오프 미팅")
    print("=" * 60)

    # GROUNDRULE.md 로드
    groundrule = load_groundrule()
    groundrule_loaded = GROUNDRULE_PATH.exists()
    print(f"\n[GROUNDRULE.md] {'로드 완료' if groundrule_loaded else '파일 없음'}")
    print(f"  → {len(groundrule.splitlines())}줄 로드됨\n")

    agents = [
        KickoffAgent("섹터 스카우트", "섹터 분석 전문가 — 어떤 섹터에 투자할지 결정하는 역할", "SECTOR_SCOUT.md"),
        KickoffAgent("차트 분석가", "차트 분석 전문가 — 진입 조건과 타이밍을 판단하는 역할", "CHART_ANALYST.md"),
        KickoffAgent("리스크 매니저", "리스크 관리 전문가 — 손절 기준과 포지션 크기를 결정하는 역할", "RISK_MANAGER.md"),
        KickoffAgent("포트폴리오 매니저", "포트폴리오 관리 전문가 — 자금 배분과 매매 실행을 담당하는 역할", "PORTFOLIO_MANAGER.md"),
    ]
    lead = KickoffLead()

    # 팀장 오프닝
    print("\n[팀장] 오프닝 발언 중...")
    lead_open = lead.open_meeting(groundrule)
    print(f"\n{'─'*40}")
    print(f"[팀장]\n{lead_open}")

    # 라운드 1: 각 에이전트가 GROUNDRULE.md를 읽고 자기 역할 및 불일치 확인
    print(f"\n{'─'*40}")
    print("\n[라운드 1] GROUNDRULE.md 기반 역할 확인 및 불일치 점검")
    verifications = {}
    for agent in agents:
        print(f"  [{agent.name}] GROUNDRULE.md 검토 중...")
        verifications[agent.name] = agent.verify_groundrule(groundrule)
        print(f"\n[{agent.name}]\n{verifications[agent.name]}")

    # 라운드 2: 상호 확인
    print(f"\n{'─'*40}")
    print("\n[라운드 2] 상호 확인 및 보완")
    confirmations = {}
    for agent in agents:
        other_reviews = "\n\n".join(
            f"[{name}]\n{v}" for name, v in verifications.items() if name != agent.name
        )
        print(f"  [{agent.name}] 상호 확인 중...")
        confirmations[agent.name] = agent.confirm_understanding(groundrule, other_reviews)
        print(f"\n[{agent.name}]\n{confirmations[agent.name]}")

    # 팀장 클로징
    print(f"\n{'─'*40}")
    print("\n[팀장] 미팅 마무리 중...")
    all_summaries = (
        "=== GROUNDRULE.md 기반 역할 확인 ===\n" +
        "\n\n".join(f"[{name}]\n{v}" for name, v in verifications.items()) +
        "\n\n=== 상호 확인 ===\n" +
        "\n\n".join(f"[{name}]\n{c}" for name, c in confirmations.items())
    )
    lead_close = lead.close_meeting(groundrule, all_summaries)
    print(f"\n[팀장]\n{lead_close}")

    # 저장
    save_results(groundrule_loaded, lead_open, verifications, confirmations, lead_close)
    print(f"\n{'='*60}")
    print(f"미팅 기록 저장: {OUTPUT}")
    print(f"{'='*60}")

    # Slack 알림
    mismatch_keywords = ["불일치", "업데이트 필요", "수정 필요", "반영 필요", "차이"]
    has_mismatch = any(kw in lead_close for kw in mismatch_keywords)
    notify_kickoff(lead_close, has_mismatch)


if __name__ == "__main__":
    main()
