@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found. Install Python and try again.
  pause
  exit /b 1
)
py -m streamlit run app.py
pause
