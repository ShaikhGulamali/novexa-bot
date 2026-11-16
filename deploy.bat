@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   NOVEXA - deploy to GitHub + Render
echo ============================================
echo.

git add -A

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set STAMP=%DT:~0,4%-%DT:~4,2%-%DT:~6,2% %DT:~8,2%:%DT:~10,2%

git diff --cached --quiet
if %ERRORLEVEL%==0 (
    echo Nothing changed - no commit needed.
) else (
    git commit -m "update %STAMP%"
    if errorlevel 1 goto fail
)

echo.
echo Pushing to GitHub...
git push
if errorlevel 1 goto fail

echo.
echo ============================================
echo   Pushed. Render auto-builds in ~2 minutes.
echo   Watch: https://dashboard.render.com/web/srv-dbt7hf56e07s73blcc6g
echo ============================================
goto end

:fail
echo.
echo DEPLOY FAILED - see the message above.
echo If it is an auth error, the GitHub token in the remote URL needs refreshing.

:end
echo.
pause
