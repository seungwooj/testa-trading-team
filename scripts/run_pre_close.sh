#!/bin/zsh
# 평일 08:00 — 장시작 전 분석
cd /Users/minerva/testa-trading-team
/usr/bin/python3 orchestrator.py mock pre_close >> logs/pre_close.log 2>&1
