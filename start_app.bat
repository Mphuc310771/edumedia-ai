@echo off
title AgentSys Studio Launcher
cd /d "%~dp0"
echo ====================================================
echo   AgentSys AI Studio - Khoi dong he thong
echo ====================================================
echo   Mode: AWS (S3, Rekognition, Transcribe, DynamoDB, Bedrock)
echo 1. Dang khoi dong Backend FastAPI tai port 8000...
start "AgentSys Backend" cmd /k "cd /d %~dp0 && python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload"

echo 2. Dang khoi dong Frontend React tai port 5174...
start "AgentSys Frontend" cmd /k "cd /d %~dp0gallery_web && npm run dev"

echo.
echo ====================================================
echo   He thong da duoc khoi dong thanh cong!
echo   - Tren Laptop:    http://localhost:5174
echo   - Tren Dien thoai: chay "ipconfig" de xem dia chi LAN
echo ====================================================
timeout /t 3 >nul
start http://localhost:5174
