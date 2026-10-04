#!/bin/zsh
DIR="/Users/minerva/testa-trading-team"
LOG="/Users/minerva/Library/Logs/testa-trading/scheduler.log"

tlog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG" }

tlog "스케줄러 시작"

last_date=""; ran_kickoff=""; ran_pre_open=""; ran_market_open=""; ran_stop_loss=""; ran_entry=""; ran_debate=""

while true; do
    now=$(date '+%H%M'); today=$(date '+%Y-%m-%d'); weekday=$(date '+%u')

    if [[ "$today" != "$last_date" ]]; then
        last_date="$today"; ran_kickoff=""; ran_pre_open=""; ran_market_open=""; ran_stop_loss=""; ran_entry=""; ran_debate=""
        tlog "날짜 초기화: $today (요일: $weekday)"
    fi

    # 월요일 07:30 — 킥오프 (주 1회)
    [[ $weekday == 1 && $now == "0730" && -z $ran_kickoff ]] && { ran_kickoff=1; tlog "kickoff 시작"; { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/team_kickoff.py" mock 2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/kickoff.log" & }

    # 평일 — 장 운영
    if [[ $weekday -le 5 ]]; then
        [[ $now == "0800" && -z $ran_pre_open   ]] && { ran_pre_open=1;   tlog "pre_open 시작";         { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/orchestrator.py" mock pre_open         2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/pre_open.log"         & }
        [[ $now == "0900" && -z $ran_market_open ]] && { ran_market_open=1; tlog "market_open 시작";       { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/orchestrator.py" mock market_open       2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/market_open.log"       & }
        [[ $now == "0905" && -z $ran_stop_loss   ]] && { ran_stop_loss=1;   tlog "stop_loss_monitor 시작"; { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/orchestrator.py" mock stop_loss_monitor 2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/stop_loss_monitor.log" & }
        [[ $now == "1000" && -z $ran_entry       ]] && { ran_entry=1;        tlog "entry_monitor 시작";    { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/orchestrator.py" mock entry_monitor     2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/entry_monitor.log"     & }
    fi

    # 토요일 10:00 — 전략 토론 (주 1회)
    [[ $weekday == 6 && $now == "1000" && -z $ran_debate ]] && { ran_debate=1; tlog "strategy_debate 시작"; { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작"; /usr/bin/python3 "$DIR/strategy_debate.py" mock 2>&1; echo "[$(date '+%Y-%m-%d %H:%M:%S')] 종료"; } >> "$DIR/logs/strategy_debate.log" & }

    sleep 30
done
