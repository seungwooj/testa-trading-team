#!/bin/zsh
# 평일 09:05~14:30 — 손절 모니터링
cd /Users/minerva/Documents/testa-trading-team
/usr/bin/python3 orchestrator.py mock stop_loss_monitor >> logs/stop_loss_monitor.log 2>&1
