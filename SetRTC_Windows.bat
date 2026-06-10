@echo off
:: EEB3 Clock — Set RTC Time (Windows)
:: Double-click this file after every Arduino upload.
:: It will open a Command Prompt, connect to the Arduino, and set the exact time.

title EEB3 Clock — RTC Time Setter

:: Move to the folder this batch file lives in
cd /d "%~dp0"

echo ================================================
echo   EEB3 Clock - RTC Time Setter
echo ================================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Download from https://www.python.org/downloads/
    echo Make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Install pyserial if missing
python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo Installing required library ^(pyserial^)...
    pip install pyserial --quiet
)

:: Run the time-setter script
python set_rtc.py

echo.
pause
