# testa-trading-team

KIS(한국투자증권) API 기반 한국 주식 자동매매 시스템.
Claude 멀티에이전트가 협업해 매매 판단을 내린다.

---

## 목적

이동평균선 정배열 + 고점 돌파 전략을 기반으로, 인간의 개입 없이 자동으로 섹터 선정 → 종목 필터링 → 매수/매도를 실행한다. 손절은 예외 없이 시스템이 집행하고, 매매 결과는 Slack으로 실시간 보고된다.

---

## 전체 투자 로직

### 핵심 원칙

1. **손절점 도달 시 반드시 손절** — 예외 없음
2. **돈이 몰리는 섹터 안에서만 거래** — 섹터 선정이 모든 것의 출발점
3. **수익 중인 종목만 보유** — 손절을 실행하면 자동으로 달성됨

---

### 1단계 — 섹터 선정

- **기준**: 업종지수 1개월 수익률 최상위 1개 섹터
- **데이터**: KIS API `inquire-daily-indexchartprice`
- **보류 조건**:

| 상황 | 결과 |
|------|------|
| 전 섹터 수익률 음수 | 당일 신규 매수 없음 |
| 1위·2위 차이 1%p 미만 | 매수 가능, 팀장이 보수적 판단 |
| 정상 | 정상 진행 |

---

### 2단계 — 종목 진입 조건 (3가지 모두 충족)

| 조건 | 기준 |
|------|------|
| 이동평균선 정배열 | 5일선 > 20일선 > 60일선 |
| 전날 종가 > 20일선 | 캔들 마감 기준 |
| 60일 우상향 추세 | 고점과 저점이 지속적으로 상승 |

**매수 타이밍**: 위 3가지 조건 충족 상태에서 `swing_high` 돌파 시 (15:00~15:30)

**swing_high 정의**: 최근 20일 내, 이후 2거래일 이상 연속 하락이 확인된 가장 최근 고점봉의 고가. 후보 없을 시 최근 20일 최고가로 fallback.

---

### 3단계 — 포지션 크기 계산

```
허용 손실액   = 가용 현금 × 2%
리스크 per 주 = 진입가 − 손절가
매수 수량     = 허용 손실액 ÷ 리스크 per 주
최대 수량     = 가용 현금 × 20% ÷ 진입가
최종 수량     = min(매수 수량, 최대 수량)
```

- 가용 현금 기준: 09:00 익절 매도 완료 후 실제 잔액
- 단일 종목 최대 투자: 현금의 20%
- 최대 보유 종목 수: 5개

---

### 손절 / 익절 기준

| 구분 | 기준 | 실행 시점 |
|------|------|-----------|
| 손절가 | 매수 시점의 20일 이동평균선 | 현재가 ≤ 손절가 즉시 매도 |
| 익절 대상 선정 | 현재가 < 20일선 (종가 마감) | 08:00 확인 |
| 익절 매도 실행 | 익절 대상 시장가 매도 | 09:00 |

---

### 동시 돌파 시 우선순위

복수 종목이 동시에 `swing_high`를 돌파할 경우:

1. 리스크 비율이 낮은 종목 먼저 — `(swing_high − ma20) / swing_high` 값이 작은 순
2. 거래량 동반 여부
3. 섹터 내 시가총액 큰 종목

포트폴리오 슬롯(5개) 초과 시 이후 종목은 당일 진입 포기.

---

## 에이전트 구성

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| 섹터 스카우트 | `agents/sector_scout.py` | 업종지수 수익률 기반 섹터 선정 |
| 차트 분석가 | `agents/chart_analyst.py` | 3조건 필터링, swing_high 산출, 실시간 감시 |
| 리스크 매니저 | `agents/risk_manager.py` | 포지션 크기 계산, 손절 모니터링 |
| 포트폴리오 매니저 | `agents/portfolio_manager.py` | 매수/매도 실행, 자금 배분 |
| 팀장 | `orchestrator.py` (TeamLead) | 각 에이전트 의견 종합 → 최종 매수 승인 또는 보류 |

각 에이전트는 `agents/*.md` 판단 지침을 시스템 프롬프트로 자동 로드한다.

**팀장 매수 승인 조건** (하나라도 미충족 시 보류):
- 차트 분석가 3조건 모두 충족
- 리스크 매니저 "적정" 또는 "소량 진입 권장"
- 섹터 강세 유지 중
- 포트폴리오 슬롯 여유 있음

---

## 전체 운영 사이클

### 주간 스케줄

| 시간 | 이벤트 | 스크립트 | 빈도 |
|------|--------|----------|------|
| 월요일 07:30 | 팀 킥오프 미팅 | `team_kickoff.py` | 주 1회 |
| 평일 08:00 | 장시작 전 분석 | `orchestrator.py pre_open` | 매일 |
| 평일 09:00 | 익절 매도 | `orchestrator.py market_open` | 매일 |
| 평일 09:05~15:30 | 손절 모니터링 | `orchestrator.py stop_loss_monitor` | 매일 |
| 평일 15:00~15:30 | 고점 돌파 감시 → 매수 | `orchestrator.py entry_monitor` | 매일 |
| 토요일 10:00 | 전략 토론 및 고도화 | `strategy_debate.py` | 주 1회 |

---

### 평일 08:00 — 장시작 전 분석 (`pre_open`)

1. **섹터 선정**: 업종지수 1개월 수익률 기준 1개 선정, 신뢰도 판단
2. **후보 종목 선정**: 선정 섹터 내 3조건 필터링
3. **보유 종목 점검**: 매수가 / 현재가 / 수익률 / 손절가 확인
4. **익절 대상 선정**: 현재가 < 20일선인 보유 종목
5. **Slack 알림**: 선정 섹터, 투자 고려 대상, 익절 대상 보고

> 섹터 선정 보류 시: 2~4단계 건너뜀, 보유 종목 관리만 진행

### 평일 09:00 — 익절 매도 (`market_open`)

1. 익절 대상 종목 시장가 매도 실행
2. Slack: 매도 완료 + 현금 잔액 보고 (15:00 포지션 계산 기준)

### 평일 09:05~15:30 — 손절 모니터링 (`stop_loss_monitor`)

1. 보유 종목 현재가를 60초 간격으로 실시간 조회
2. 현재가 ≤ 손절가 도달 시 즉시 시장가 매도 실행
3. Slack: 손절 종목·수량·가격 보고
4. 보유 종목 없으면 즉시 종료
- `entry_monitor`(15:00~)와 병렬 실행, 역할은 완전히 분리

### 평일 15:00~15:30 — 고점 돌파 감시 (`entry_monitor`)

1. 투자 고려 대상 종목 현재가 실시간 감시 (60초 간격)
2. 현재가 ≥ swing_high 돌파 감지
3. 리스크 매니저: 포지션 크기 계산
4. 팀장: 섹터·차트·리스크 종합 → 매수 승인 또는 보류
5. 승인 시 즉시 매수, 손절가 = 매수 시점 20일선
6. 15:30까지 진입 없으면 Slack "매수 없음" 보고

### 월요일 07:30 — 팀 킥오프 미팅 (`team_kickoff.py`)

- 에이전트 전원이 전체 매매 흐름을 함께 숙지
- Round 1: 각자 자신의 역할·입출력·주의사항 검토
- Round 2: 다른 에이전트의 역할 교차 확인
- 결과: `data/kickoff_notes.md` 저장

### 토요일 10:00 — 전략 토론 (`strategy_debate.py`)

- 에이전트들이 정해진 주제로 토론 (`DEBATE_TOPICS` 직접 편집 가능)
- Round 1: 각자 문제점·개선 의견 제시
- Round 2: 상호 검토 및 보완
- 팀장이 실행 가능한 개선안으로 종합
- 결과: `data/strategy_notes.md` 저장

---

## 폴더 구조

```
testa-trading-team/
│
├── GROUNDRULE.md              # 전략 단일 진실 공급원 (Single Source of Truth)
├── CLAUDE.md                  # Claude Code 프로젝트 지침
├── README.md                  # 이 문서
├── config.py                  # 환경변수 로드 (.env.mock / .env.real)
├── requirements.txt           # 의존 패키지
│
├── orchestrator.py            # 실행 진입점 (pre_open / market_open / stop_loss_monitor / entry_monitor)
├── team_kickoff.py            # 월요일 팀 킥오프 미팅
├── strategy_debate.py         # 주말 전략 토론
│
├── agents/
│   ├── base_agent.py          # Claude API 호출 공통 (specs/ 자동 로드)
│   ├── sector_scout.py        # 섹터 선정 (업종지수 수익률)
│   ├── chart_analyst.py       # 종목 필터링 (3조건 + swing_high)
│   ├── risk_manager.py        # 포지션 크기 계산, 손절 실행
│   ├── portfolio_manager.py   # 매수/매도 실행, 자금 배분
│   └── specs/                 # 에이전트 판단 지침 (.md)
│       ├── SECTOR_SCOUT.md
│       ├── CHART_ANALYST.md
│       ├── RISK_MANAGER.md
│       ├── PORTFOLIO_MANAGER.md
│       └── TEAM_LEAD.md
│
├── tools/
│   ├── kis_auth.py            # KIS 토큰 발급 + 파일 캐싱
│   ├── kis_market.py          # 시세 조회 (종목 OHLCV, 현재가, 업종지수)
│   ├── kis_order.py           # 주문 실행 (buy / sell / get_balance)
│   ├── technical.py           # 기술적 분석 (이동평균, swing_high, 추세)
│   └── slack.py               # Slack Webhook 알림
│
├── scripts/                   # 자동 실행 스크립트 + 유틸
│   ├── run_kickoff.sh         # launchd 래퍼 (월 07:30)
│   ├── run_pre_open.sh       # launchd 래퍼 (평일 08:00)
│   ├── run_market_open.sh     # launchd 래퍼 (평일 09:00)
│   ├── run_stop_loss_monitor.sh  # launchd 래퍼 (평일 09:05)
│   ├── run_entry_monitor.sh   # launchd 래퍼 (평일 15:00)
│   ├── run_strategy_debate.sh # launchd 래퍼 (토 10:00)
│   ├── setup_sectors.py       # sectors.json 초기화 (최초 1회)
│   ├── build_sectors_from_krx.py  # KOSPI 전체 섹터-종목 매핑 생성
│   └── make_sector_stock_mapping.py
│
├── data/
│   ├── sectors.json           # 섹터별 종목 목록 + 업종코드 (직접 편집 가능)
│   ├── candidates.json        # 당일 투자 고려 대상 (단계 간 상태 전달)
│   ├── profit_targets.json    # 당일 익절 대상
│   ├── stop_losses.json       # 종목별 손절가 (영구 보관, 초기화 주의)
│   ├── kickoff_notes.md       # 팀 킥오프 미팅 기록
│   └── strategy_notes.md      # 전략 토론 결과
│
└── logs/                      # 자동 실행 로그 (launchd)
    ├── pre_open.log
    ├── market_open.log
    ├── stop_loss_monitor.log
    ├── entry_monitor.log
    ├── kickoff.log
    └── strategy_debate.log
```

---

## 설치 및 초기 설정

### 1. 의존 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env.mock` (모의투자) 또는 `.env.real` (실전투자) 파일 생성:

```env
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
KIS_TRADE_URL=https://openapivts.koreainvestment.com:29443   # mock
# KIS_TRADE_URL=https://openapi.koreainvestment.com:9443    # real
KIS_TR_BUY=VTTC0802U     # mock: VTTC0802U / real: TTTC0802U
KIS_TR_SELL=VTTC0801U    # mock: VTTC0801U / real: TTTC0801U
KIS_TR_BALANCE=VTTC8434R # mock: VTTC8434R / real: TTTC8434R
ANTHROPIC_API_KEY=...
SLACK_WEBHOOK_URL=...
```

### 3. 섹터-종목 데이터 초기화

```bash
# KOSPI 전체 종목 기반 (KIND 공개 데이터, 835개 종목 / 21개 섹터)
python build_sectors_from_krx.py

# 또는 5개 핵심 섹터만 빠르게 설정
python setup_sectors.py mock
```

---

## 실행 방법

### 수동 실행

```bash
# 08:00 — 장시작 전 분석
python orchestrator.py mock pre_open

# 09:00 — 익절 매도
python orchestrator.py mock market_open

# 09:05~15:30 — 손절 모니터링
python orchestrator.py mock stop_loss_monitor

# 15:00~15:30 — 고점 돌파 감시 → 매수
python orchestrator.py mock entry_monitor

# 월요일 킥오프 미팅
python team_kickoff.py mock

# 주말 전략 토론
python strategy_debate.py mock
```

`mock` → `real` 로 바꾸면 실전 투자 모드로 전환된다.

### 자동 실행 (macOS launchd)

아래 명령어로 스케줄 등록 / 해제:

```bash
# 등록
launchctl load ~/Library/LaunchAgents/com.testa.trading.pre_open.plist
launchctl load ~/Library/LaunchAgents/com.testa.trading.market_open.plist
launchctl load ~/Library/LaunchAgents/com.testa.trading.entry_monitor.plist
launchctl load ~/Library/LaunchAgents/com.testa.trading.kickoff.plist
launchctl load ~/Library/LaunchAgents/com.testa.trading.strategy_debate.plist

# 등록 확인
launchctl list | grep com.testa

# 해제 (일시 정지)
launchctl unload ~/Library/LaunchAgents/com.testa.trading.pre_open.plist
```

> **주의**: Mac이 잠들어 있으면 실행되지 않는다. 해당 시간에 Mac이 깨어 있어야 한다.

### 실전 전환 시

1. `run_*.sh` 파일에서 `mock` → `real` 로 변경
2. launchd 재등록:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.testa.trading.*.plist
   launchctl load ~/Library/LaunchAgents/com.testa.trading.*.plist
   ```

---

## KIS API 주요 참고사항

- `custtype: P` 헤더: 차트 API 호출 시 필수
- 업종지수 조회 TR: `FHKUP03500100`, 응답 키: `output2`
- `get_balance()`: 장 외 시간 500 에러 → try/except 필수
- mock API 히스토리 한계: 30~60행 (실전은 정상)

### 업종코드 매핑 (주요 5개)

| 섹터 | KIS 업종코드 |
|------|-------------|
| 반도체 (전기전자) | 1013 |
| 2차전지 (화학) | 1008 |
| 바이오 (의약품) | 1009 |
| 자동차 (운수장비) | 1015 |
| 금융업 | 1021 |

전체 21개 섹터 매핑은 `data/sectors.json` 참고.

---

## 전략 변경 시 주의사항

- 손절/익절 조건은 핵심 전략 — **임의 변경 금지**
- `data/sectors.json`: 사용자가 직접 편집 가능, 덮어쓰지 말 것
- `data/stop_losses.json`: 영구 상태 — 초기화 전 반드시 확인
- 전략 변경 시 `GROUNDRULE.md` 먼저 수정 → 코드 반영 순서 준수
- 에이전트 `.md` 파일 수정 시 전략 방향성 유지

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
