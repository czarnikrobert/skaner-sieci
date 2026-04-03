@echo off
:: Sprawdź uprawnienia administratora
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Uruchamianie jako Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
python main.py
pause
