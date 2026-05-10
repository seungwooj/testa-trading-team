import anthropic
from pathlib import Path
from typing import Optional
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

AGENTS_DIR = Path(__file__).parent / "specs"


class BaseAgent:
    SPEC_FILE: Optional[str] = None  # 서브클래스에서 "AGENT_NAME.md" 형태로 지정

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self._spec = self._load_spec()

    def _load_spec(self) -> str:
        if self.SPEC_FILE is None:
            return ""
        path = AGENTS_DIR / self.SPEC_FILE
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def think(self, prompt: str) -> str:
        system = f"당신은 주식 트레이딩 팀의 {self.role}입니다. 분석 결과를 간결하고 명확하게 한국어로 답변하세요."
        if self._spec:
            system += f"\n\n---\n{self._spec}"

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
