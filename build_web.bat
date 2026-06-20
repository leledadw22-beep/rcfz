@echo off
REM Builds dist\ - ONLY the files safe to host publicly (NO .env, NO .py, NO keys).
REM Host the dist\ folder (e.g. drag it to https://app.netlify.com/drop).
cd /d "%~dp0"
if not exist dist mkdir dist
if not exist dist\data mkdir dist\data
copy /Y index.html dist\ >nul
copy /Y manifest.webmanifest dist\ >nul
copy /Y sw.js dist\ >nul
copy /Y icon-192.png dist\ >nul
copy /Y icon-512.png dist\ >nul
copy /Y data\videos.js dist\data\ >nul
echo.
echo Built dist\  -  host THIS folder (no secrets inside).
echo Re-run this after each refresh.bat to push fresh data.
