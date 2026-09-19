@echo off
title Install Requirements - CapCut Checker Web
echo ======================================================
echo   Menginstall library yang dibutuhkan (flask, requests)
echo ======================================================
echo.

pip install flask requests

echo.
echo ======================================================
if %ERRORLEVEL% equ 0 (
    echo   [SUKSES] Semua library berhasil diinstall!
) else (
    echo   [GAGAL] Terjadi kesalahan saat install library.
    echo   Pastikan Python dan pip sudah terpasang di sistem.
)
echo ======================================================
echo.
pause
