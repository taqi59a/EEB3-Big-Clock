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

:: Find Python — try "python", then "py" launcher, then "python3"
set PYTHON=
python --version >nul 2>&1
if not errorlevel 1 set PYTHON=python

if "%PYTHON%"=="" (
    py --version >nul 2>&1
    if not errorlevel 1 set PYTHON=py
)

if "%PYTHON%"=="" (
    python3 --version >nul 2>&1
    if not errorlevel 1 set PYTHON=python3
)

if "%PYTHON%"=="" (
    echo ERROR: Python not found.
    echo Download from https://www.python.org/downloads/
    echo Make sure to tick "Add Python to PATH" during install.
    echo Then close and re-open this window.
    pause
    exit /b 1
)

echo Using: %PYTHON%

:: Install pyserial if missing (use python -m pip to match the right install)
%PYTHON% -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo Installing required library ^(pyserial^)...
    %PYTHON% -m pip install pyserial --quiet
)

:: Run the time-setter script
%PYTHON% set_rtc.py

echo.
pause
