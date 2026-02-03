@echo off
chcp 65001 > nul
echo ============================================
echo  Chrome Debug Mode
echo ============================================
echo.

taskkill /F /IM chrome.exe 2>nul
ping 127.0.0.1 -n 3 > nul

set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME_PATH%" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

echo Starting Chrome with debug port 9222...
echo.

start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug"

echo.
echo Chrome started in debug mode.
echo Now run: python korail_debug.py
echo.
pause
