@echo off
echo ========================================
echo  Stopping Milvus Vector Database
echo ========================================
echo.

cd /d "%~dp0"

echo Stopping Docker containers...
docker-compose down

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to stop containers
    pause
    exit /b 1
)

echo.
echo ========================================
echo  All Services Stopped
echo ========================================
echo.
echo To start again: start.bat
echo.
pause
