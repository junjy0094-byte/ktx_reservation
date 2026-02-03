@echo off
echo ============================================
echo  Chrome 디버그 모드 실행
echo ============================================
echo.

REM 기존 Chrome 프로세스 종료
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

REM Chrome 경로 (일반적인 설치 경로)
set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"

REM Chrome이 없으면 다른 경로 시도
if not exist %CHROME_PATH% (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

echo Chrome 실행 중...
echo 디버그 포트: 9222
echo.

start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile"

echo.
echo Chrome이 디버그 모드로 실행되었습니다.
echo 이제 python korail_debug.py 를 실행하세요.
echo.
pause
