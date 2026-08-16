@echo off
title AgentSys Studio Launcher
echo ====================================================
echo   AgentSys AI Studio - Khoi dong he thong
echo ====================================================
echo 1. Dang khoi dong Backend FastAPI tai port 8000...
start "AgentSys Backend" cmd /k "cd /d %~dp0 && python -m uvicorn apps.api.main:app --port 8000 --reload"

echo 2. Dang khoi dong Frontend React tai port 5174...
start "AgentSys Frontend" cmd /k "cd /d %~dp0gallery_web && npm run dev"

echo.
echo ====================================================
echo   He thong da duoc khoi dong thanh cong!
echo   Trinh duyet: http://localhost:5174
echo ====================================================
timeout /t 3 >nul
start http://localhost:5174
