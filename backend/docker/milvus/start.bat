@echo off
echo ========================================
echo  Starting Milvus Vector Database
echo ========================================
echo.
echo Services starting:
echo   - Milvus (Vector Database)
echo   - MinIO (Object Storage)
echo   - etcd (Metadata Store)
echo   - Pulsar (Message Queue)
echo.

cd /d "%~dp0"

echo Starting Docker containers...
docker-compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start containers
    echo Please check Docker Desktop is running
    pause
    exit /b 1
)

echo.
echo Waiting for services to initialize...
echo This takes about 60-90 seconds...
timeout /t 20 /nobreak > nul
echo.

echo Checking container status...
docker-compose ps

echo.
echo ========================================
echo  Services Started Successfully!
echo ========================================
echo.
echo Milvus API:       localhost:19530
echo Milvus Health:    http://localhost:9091/healthz
echo MinIO Console:    http://localhost:9001
echo   Username:       minioadmin
echo   Password:       minioadmin
echo.
echo To stop services: stop.bat
echo To check status:  status.bat
echo.
pause
