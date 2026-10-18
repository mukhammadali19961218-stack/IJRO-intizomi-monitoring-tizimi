@echo off
chcp 65001 >nul
title IJRO INTIZOMI MONITORING DASHBOARD (IES)
color 0B

echo ======================================================================
echo    IJRO INTIZOMI MONITORING TIZIMI (IES) - ISHGA TUSHIRISH
echo ======================================================================
echo.

:: 1. Check Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [XATO] Kompyuterda Node.js topilmadi!
    echo Iltimos, avval Node.js (v18 yoki undan yuqori) o'rnating: https://nodejs.org
    pause
    exit /b 1
)

:: 2. Check and install backend dependencies if needed
if not exist "server\node_modules" (
    echo [1/3] Backend paketlari o'rnatilmoqda...
    cd server
    call npm install
    cd ..
)

:: 3. Check and build frontend if dist missing
if not exist "frontend\dist" (
    echo [2/3] Frontend ilovasi yig'ilmoqda (build)...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo [3/3] Server ishga tushirilmoqda...
echo.
echo Manzil: http://127.0.0.1:8000
echo Standart login: admin
echo Standart parol: admin123
echo.
echo Dasturni to'xtatish uchun: Ushbu oynada Ctrl + C tugmalarini bosing.
echo ======================================================================
echo.

:: 4. Start Browser automatically
start http://127.0.0.1:8000

:: 5. Launch Node.js Server
cd server
node src/index.js
pause
