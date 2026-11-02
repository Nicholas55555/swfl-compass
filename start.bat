@echo off
REM SWFL Compass - one-click start (Windows). Needs Docker Desktop running.
REM First run: creates the Python venv and installs npm packages.
cd /d "%~dp0"

if not exist backend\.venv (
  echo Creating Python venv...
  python -m venv backend\.venv || goto :error
  backend\.venv\Scripts\python -m pip install -r backend\requirements.txt || goto :error
)
if not exist backend\.env (
  copy backend\.env.example backend\.env >nul
  echo.
  echo  ** Add your GEMINI_API_KEY (and GOOGLE_MAPS_API_KEY) to backend\.env, then run start.bat again. **
  notepad backend\.env
  exit /b 1
)
if not exist frontend\node_modules (
  echo Installing frontend packages...
  pushd frontend && call npm install && popd
)

start "SWFL Compass API" cmd /k backend\.venv\Scripts\python backend\run.py
start "SWFL Compass UI" cmd /k "cd frontend && npm run dev"
timeout /t 6 >nul
start http://localhost:5173
exit /b 0

:error
echo Setup failed. See the message above.
exit /b 1
