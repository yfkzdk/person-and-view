@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Voice AI System - Start All
echo ========================================
echo.

echo [1/3] Starting backend (port 8765)...
start "VoiceAI-Backend" cmd /k "cd /d O:\AII\app\voices && python run_server_auto_port.py"
timeout /t 3 /nobreak >nul

echo [2/3] Starting frontend (port 3000)...
start "VoiceAI-Frontend" cmd /k "cd /d O:\AII\app\voices\frontend && npx next dev"
timeout /t 2 /nobreak >nul

echo [3/3] Done!
echo.
echo   Backend:  http://localhost:8765
echo   Frontend: http://localhost:3000
echo.
echo   Close the two terminal windows to stop.
echo ========================================
