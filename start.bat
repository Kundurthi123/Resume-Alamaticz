@echo off
echo ================================================
echo  Hire AI - Starting Backend and Frontend
echo ================================================

:: Set NODE path
set "PATH=%PATH%;C:\Program Files\nodejs"

:: Start FastAPI backend in its own window
echo Starting FastAPI backend on port 8000...
Start "Hire AI - Backend" /D "%~dp0" python -m uvicorn backend.main:app --reload --port 8000

:: Give backend 4 seconds to start
timeout /t 4 /nobreak >nul

:: Start React dev server in its own window
echo Starting React frontend on port 5173...
Start "Hire AI - Frontend" /D "%~dp0\frontend" cmd /c "set PATH=%PATH%;C:\Program Files\nodejs && npm run dev"

echo.
echo ================================================
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo  API Docs: http://localhost:8000/docs
echo ================================================
timeout /t 5 /nobreak >nul
start http://localhost:5173
