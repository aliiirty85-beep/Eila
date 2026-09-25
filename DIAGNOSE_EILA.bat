@echo off
setlocal
cd /d %~dp0
title Eila Diagnostics

echo ========================================
echo Eila Diagnostics
echo ========================================
echo.

if not exist .venv\Scripts\python.exe (
  echo [FAIL] .venv not found. Double-click START_EILA.bat first.
  pause
  exit /b 1
)

echo [1/3] Doctor
.venv\Scripts\python.exe doctor.py
echo.

echo [2/3] Live Core health
powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 3; $r | ConvertTo-Json -Depth 8 } catch { Write-Host ('[FAIL] health: '+$_.Exception.Message) }"
echo.

echo [3/3] Last Core log lines
powershell -NoProfile -Command "if (Test-Path '.\logs\core.log') { Get-Content '.\logs\core.log' -Tail 35 } else { Write-Host '[INFO] core.log does not exist yet.' }"
echo.
echo Send a screenshot of this window when reporting a startup problem.
pause
