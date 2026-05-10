#!/bin/zsh
# 평일 09:00 — 익절 매도
cd /Users/minerva/Documents/testa-trading-team
/usr/bin/python3 orchestrator.py mock market_open >> logs/market_open.log 2>&1
