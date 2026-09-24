@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (call setup_windows.bat & exit /b %errorlevel%)
call .venv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
python doctor.py
if errorlevel 1 echo Doctor found a critical problem. Check logs\launcher.log and data\backups.
pause
