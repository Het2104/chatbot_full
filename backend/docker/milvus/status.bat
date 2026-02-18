@echo off
echo ========================================
echo  Milvus Services Status
echo ========================================
echo.

cd /d "%~dp0"

docker-compose ps

echo.
echo Health Status:
echo.

echo [Milvus Standalone]
curl -s http://localhost:9091/healthz > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Status: HEALTHY
) else (
    echo   Status: NOT RUNNING
)

echo.
echo [MinIO]
curl -s http://localhost:9000/minio/health/live > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Status: HEALTHY
) else (
    echo   Status: NOT RUNNING
)

echo.
echo ========================================
echo.
pause
