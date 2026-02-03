#!/bin/bash

echo "============================================"
echo " Chrome 디버그 모드 실행"
echo "============================================"
echo

# 기존 Chrome 프로세스 종료
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# OS 확인
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    # Linux
    CHROME_PATH="google-chrome"
fi

echo "Chrome 실행 중..."
echo "디버그 포트: 9222"
echo

"$CHROME_PATH" --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debug_profile" &

echo
echo "Chrome이 디버그 모드로 실행되었습니다."
echo "이제 python korail_debug.py 를 실행하세요."
echo
