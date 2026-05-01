@echo off
title Astra Engine with AI Gateway

echo 🚀 Starting Astra Engine with AI Gateway...

REM Check if .env file exists
if not exist ".env" (
    echo ❌ Error: .env file not found. Please copy .env.example to .env and configure your API keys.
    pause
    exit /b 1
)

REM Start LiteLLM proxy in background
echo 🔧 Starting LiteLLM proxy on port 4000...
cd ../backend
start "LiteLLM Proxy" cmd /c "litellm --config config.yaml --port 4000"

REM Wait for LiteLLM to start
echo ⏳ Waiting for LiteLLM proxy to start...
timeout /t 5 /nobreak > nul

REM Start Astra backend in background
echo 🧠 Starting Astra backend...
start "Astra Backend" cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait for Astra backend to start
echo ⏳ Waiting for Astra backend to start...
timeout /t 10 /nobreak > nul

echo.
echo 🎉 Astra Engine is ready!
echo 📍 Astra Backend: http://localhost:8000
echo 📍 LiteLLM Proxy: http://localhost:4000
echo 📍 Health Check: http://localhost:8000/health
echo 📍 Gateway Health: http://localhost:8000/gateway/health
echo.
echo Close this window to stop all services

REM Keep the script running
pause
