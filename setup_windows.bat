@echo off
setlocal
cd /d %~dp0

set "PYEXE="
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.12 -c "import sys" >nul 2>nul && set "PYEXE=py -3.12"
  if not defined PYEXE py -3.11 -c "import sys" >nul 2>nul && set "PYEXE=py -3.11"
)

if not defined PYEXE (
  where python >nul 2>nul || (
    echo Compatible Python not found.
    echo Install Python 3.12 or 3.11, then run setup_windows.bat again.
    exit /b 1
  )
  for /f "tokens=2 delims= " %%V in ('python -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))"') do set "PYVER=%%V"
  python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul || (
    echo Found Python, but Eila requires Python 3.11 or 3.12.
    echo Current:
    python --version
    echo Install Python 3.12 or 3.11, or ensure the Python Launcher "py" is available.
    exit /b 1
  )
  set "PYEXE=python"
)

echo Using %PYEXE%
if exist .venv (
  .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul
  if not %errorlevel%==0 (
    echo Existing .venv uses an incompatible Python. Rebuilding it...
    rmdir /s /q .venv
  )
)

if not exist .venv %PYEXE% -m venv .venv
if not exist .venv\Scripts\python.exe (
  echo Failed to create .venv
  exit /b 1
)

.venv\Scripts\python.exe -m pip install --upgrade pip || exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt || exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt || exit /b 1
.venv\Scripts\python.exe doctor.py
set "RC=%errorlevel%"
if not "%RC%"=="0" (
  echo Eila Doctor reported a critical setup problem.
  exit /b %RC%
)
echo Setup complete.
pause
