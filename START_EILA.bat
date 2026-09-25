@echo off
setlocal
cd /d %~dp0
title Eila One-Click Start

if not exist .venv\Scripts\python.exe (
  echo First run: preparing Eila...
  set EILA_NO_PAUSE=1
  call setup_windows.bat
  if errorlevel 1 (
    echo Setup failed. See the message above.
    pause
    exit /b 1
  )
)

.venv\Scripts\python.exe start_eila.py
set "RC=%errorlevel%"
if not "%RC%"=="0" (
  echo.
  echo Eila could not start cleanly. Error code %RC%.
  pause
)
exit /b %RC%
