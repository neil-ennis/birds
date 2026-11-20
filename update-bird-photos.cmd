@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 (
    echo Could not open the Birds repository folder.
    set "result=1"
    goto done
)

python scripts\update_bird_photos.py %*
set "result=%errorlevel%"

:done
echo.
if "%result%"=="0" (
    echo Bird photo catalogue check completed.
) else (
    echo Some photos still need attention. See the messages above.
)
echo Press any key to close this window.
pause >nul
exit /b %result%
