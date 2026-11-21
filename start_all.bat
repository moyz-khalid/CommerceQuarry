@echo off
title CommerceQuarry Sourcing Platform
echo ===================================================
echo   Starting CommerceQuarry Full-Stack Platform
echo ===================================================
echo Starting FastAPI Backend (Port 8000)...
start "CommerceQuarry Backend" "%~dp0start_backend.bat"
timeout /t 2 >nul
echo Starting Next.js Frontend (Port 3000)...
start "CommerceQuarry Frontend" "%~dp0start_frontend.bat"
echo.
echo Both servers are launching!
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo ===================================================
pause
