# testa-trading-team — 프로젝트 지침

## 프로젝트 개요
KIS(한국투자증권) API를 이용한 한국 주식 자동매매 시스템.
Claude 멀티에이전트가 협업해 매매 판단을 내린다.

## 매매 전략 (절대 임의로 변경 금지)

### 진입 조건
1. 이동평균선 정배열: 5일 > 20일 > 60일
2. 전날 종가 > 20일 이동평균선 (캔들 마감 기준)
3. 최근 60일 우상향 추세 (고점·저점 지속 상승)
4. 위 3가지 만족 + 눌림목 이전 고점 돌파 시 매수 (15:00~15:30)

### 손절/익절
- 손절가: 매수 시점의 20일 이동평균선 가격
- 익절: 현재 주가가 20일선 아래에서 마감될 때 (다음날 09:00 매도)

### 하루 운영 흐름
- 08:00: 섹터 선정(업종지수 1개월 수익률 최상위) + 후보 종목 필터링 + 익절 대상 확인
- 09:00: 익절 대상 종목 시장가 매도
- 09:05~15:30: 손절 모니터링 (60초 간격, 손절가 도달 시 즉시 매도)
- 15:00~15:30: 고점 돌파 감시 → 즉시 매수

## 실행 방법
```bash
python orchestrator.py mock pre_open           # 08:00 단계
python orchestrator.py mock market_open         # 09:00 단계
python orchestrator.py mock stop_loss_monitor   # 09:05~15:30 단계
python orchestrator.py mock entry_monitor       # 15:00~15:30 단계

python strategy_debate.py mock            # 전략 토론 (필요 시)
python setup_sectors.py mock              # sectors.json 초기화 (최초 1회)
```

## 파일 구조
```
orchestrator.py          진입점 (pre_open / market_open / stop_loss_monitor / entry_monitor)
strategy_debate.py       에이전트 전략 토론
team_kickoff.py          팀 킥오프 미팅
config.py                환경변수 (.env.mock / .env.real)
agents/
  base_agent.py          Claude API 호출 공통 (specs/ 자동 로드)
  sector_scout.py        섹터 선정 (업종지수 수익률 기준)
  chart_analyst.py       종목 필터링 (3조건)
  risk_manager.py        포지션 크기 / 손절 실행
  portfolio_manager.py   자금 배분 / 매수 실행
  specs/
    SECTOR_SCOUT.md      섹터 스카우트 판단 지침
    CHART_ANALYST.md     차트 분석가 판단 지침
    RISK_MANAGER.md      리스크 매니저 판단 지침
    PORTFOLIO_MANAGER.md 포트폴리오 매니저 판단 지침
    TEAM_LEAD.md         팀장 판단 지침
tools/
  kis_auth.py            KIS 토큰 발급 + 파일 캐싱
  kis_market.py          시세 조회 (get_daily_ohlcv, get_current_price, get_index_ohlcv)
  kis_order.py           주문 실행 (buy, sell, get_balance)
  technical.py           기술적 분석 (이동평균, 스윙고점, 추세)
  slack.py               Slack Webhook 알림
scripts/
  run_*.sh               launchd 래퍼 셸 스크립트
  setup_sectors.py       sectors.json 초기화 (최초 1회)
  build_sectors_from_krx.py  KOSPI 전 종목 섹터 매핑 생성
data/
  sectors.json           섹터별 종목 목록 + 업종코드 (직접 편집 가능)
  candidates.json        당일 투자 고려 대상 (단계 간 상태 전달)
  profit_targets.json    당일 익절 대상
  stop_losses.json       종목별 손절가 (영구 보관)
  kickoff_notes.md       팀 킥오프 미팅 기록
  strategy_notes.md      에이전트 토론 결과
logs/                    자동 실행 로그
```

## KIS API 주의사항
- `custtype: P` 헤더: 차트 API 필수
- `FID_INPUT_DATE_1/2`: inquire-daily-itemchartprice 필수 파라미터
- 응답 키: 종목 차트는 `output`, 업종 차트는 `output2`
- mock API: 히스토리 30~60행 한계 (실전은 정상)
- `get_balance()`: 장외 시간 500 에러 → try/except 필수
- mock/real 구분: `.env.mock`, `.env.real` — `sys.argv[1]`로 선택

## 코드 수정 시 주의
- 손절/익절 조건은 사용자 전략 핵심 — 임의 변경 금지
- `sectors.json` 파일은 사용자가 직접 편집하므로 덮어쓰지 말 것
- `data/stop_losses.json`은 영구 상태 — 초기화 전에 반드시 확인
- 에이전트 `.md` 파일 수정 시 전략 방향성 유지할 것
