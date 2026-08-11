#!/bin/bash
# 콘솔 크롤링 모드 실행 스크립트
# 사용법: ./run_console.sh all | last [타이머분]
cd "$(dirname "$0")"
source venv/bin/activate
python -u console_main.py "$@"
