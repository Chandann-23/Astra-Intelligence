# Astra Engine Simple PowerShell Startup Script

Write-Host "Starting Astra Engine with AI Gateway..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Error: .env file not found. Please copy .env.example to .env" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start LiteLLM proxy in background
Write-Host "Starting LiteLLM proxy on port 4000..." -ForegroundColor Blue
Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "-m", "litellm", "--config", "../backend/config.yaml", "--port", "4000"

# Wait for LiteLLM to start
Write-Host "Waiting for LiteLLM proxy to start..." -ForegroundColor Blue
Start-Sleep -Seconds 8

# Check if LiteLLM is running
try {
    $response = & curl.exe -s http://localhost:4000/health 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "LiteLLM proxy is running" -ForegroundColor Green
    } else {
        Write-Host "Error: LiteLLM proxy failed to start" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "Error: Cannot connect to LiteLLM proxy" -ForegroundColor Red
    exit 1
}

# Start Astra backend
Write-Host "Starting Astra backend..." -ForegroundColor Blue
Set-Location ../backend
Start-Process -WindowStyle Hidden -FilePath "uvicorn" -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"

# Wait for Astra backend to start
Write-Host "Waiting for Astra backend to start..." -ForegroundColor Blue
Start-Sleep -Seconds 12

# Check if Astra backend is running
try {
    $response = & curl.exe -s http://localhost:8000/health 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Astra backend is running" -ForegroundColor Green
    } else {
        Write-Host "Error: Astra backend failed to start" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "Error: Cannot connect to Astra backend" -ForegroundColor Red
    exit 1
}

# Display service URLs
Write-Host ""
Write-Host "Astra Engine is ready!" -ForegroundColor Green
Write-Host "Astra Backend: http://localhost:8000"
Write-Host "LiteLLM Proxy: http://localhost:4000"
Write-Host "Health Check: http://localhost:8000/health"
Write-Host "Gateway Health: http://localhost:8000/gateway/health"
Write-Host ""
Write-Host "Services are running in background windows."
Write-Host "Close the windows to stop the services."
