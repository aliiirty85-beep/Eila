@echo off
cd /d %~dp0
if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe show_pairing_token.py) else (python show_pairing_token.py)
pause
