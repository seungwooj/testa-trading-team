#!/bin/zsh
# 평일 15:00 — 고점 돌파 감시 → 매수
cd /Users/minerva/testa-trading-team
/usr/bin/python3 orchestrator.py mock entry_monitor >> logs/entry_monitor.log 2>&1
