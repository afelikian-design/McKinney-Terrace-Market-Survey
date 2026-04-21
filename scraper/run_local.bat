@echo off
REM Run the scraper locally and push the refreshed data to GitHub.
REM Usage: double-click, or: scraper\run_local.bat

setlocal
cd /d "%~dp0\.."

echo Running scraper...
pushd scraper
python scrape.py
if errorlevel 1 (
  echo Scraper failed with exit code %errorlevel%.
  popd
  exit /b %errorlevel%
)
popd

echo Committing data\data.json...
git add data\data.json
git diff --staged --quiet
if errorlevel 1 (
  for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-ddTHH:mm:ssZ"') do set TS=%%i
  git commit -m "chore: update apartment data %TS%"
  echo Pushing to origin/main...
  git push origin main
) else (
  echo No changes to data.json - nothing to push.
)

echo Done.
endlocal
