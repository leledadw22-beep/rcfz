@echo off
REM RC Flight Zone — one-click refresh. Double-click this to pull the latest
REM trending videos and open the dashboard. Pass --demo to preview sample data.
cd /d "%~dp0"
echo ============================================
echo   RC FLIGHT ZONE - fetching what's hot...
echo ============================================
python fetch_trending.py %*
if errorlevel 1 (
  echo.
  echo Something went wrong above. Fix it, then run this again.
  pause
  exit /b 1
)
echo.
echo Opening dashboard...
start "" "%~dp0index.html"
