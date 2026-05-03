@echo off
echo ========================================
echo Real-time Voice Narrative System
echo ========================================
echo.

echo [1/2] Checking Python...
"C:\Users\yfk\AppData\Local\Programs\Python\Python311\python.exe" --version
if errorlevel 1 (
    echo ERROR: Python 3.11 not found
    pause
    exit /b 1
)

echo.
echo [2/2] Starting server...
echo.
echo Server will auto-select an available port (8000-8099)
echo Check the output below for the actual port number.
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

"C:\Users\yfk\AppData\Local\Programs\Python\Python311\python.exe" run_server_auto_port.py

pause