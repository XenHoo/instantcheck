@echo off
title CapCut Checker Web
echo ======================================================
echo   Menjalankan CapCut Checker Web Server...
echo ======================================================
echo.
echo   Buka browser di: http://localhost:5000
echo   Tekan Ctrl+C di terminal ini untuk mematikan server.
echo.
echo ======================================================
echo.

:: Otomatis membuka browser setelah server jalan (delay 2 detik di background)
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

python app.py

pause
