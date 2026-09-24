@echo off
setlocal
cd /d %~dp0
where python >nul 2>nul || (echo Python not found & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python doctor.py
pause
