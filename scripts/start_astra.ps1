# Astra Engine PowerShell Startup Script
# Optimized for Windows with proper background job handling

Write-Host "🚀 Starting Astra Engine with AI Gateway..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ Error: .env file not found. Please copy .env.example to .env and configure your API keys." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Function to check if port is in use
function Test-Port {
    param($Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to cleanup background jobs
function Cleanup-Jobs {
    Write-Host "🛑 Shutting down services..." -ForegroundColor Yellow
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    exit 0
}

# Set trap to cleanup on script exit
trap { Cleanup-Jobs } SIGINT SIGTERM

# Check if port 4000 is already in use
if (Test-Port -Port 4000) {
    Write-Host "⚠️  Port 4000 is already in use. Attempting to free it..." -ForegroundColor Yellow
    
    # Try to find and kill processes using port 4000
    try {
        $processes = Get-NetTCPConnection -LocalPort 4000 -ErrorAction SilentlyContinue
        if ($processes) {
            foreach ($proc in $processes) {
                $owningProcess = Get-Process -Id $proc.OwningProcess -ErrorAction SilentlyContinue
                if ($owningProcess) {
                    Write-Host "   Stopping process $($owningProcess.ProcessName) (PID: $($proc.OwningProcess))" -ForegroundColor Yellow
                    $owningProcess.Kill()
                }
            }
            Start-Sleep -Seconds 2
        }
    }
    catch {
        Write-Host "   Could not automatically free port 4000. Please manually stop any services using it." -ForegroundColor Yellow
    }
}

# Start LiteLLM proxy in background job
Write-Host "🔧 Starting LiteLLM proxy on port 4000..." -ForegroundColor Blue

$proxyJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python -m litellm --config ../backend/config.yaml --port 4000
} -Name "LiteLLM-Proxy"

# Wait for LiteLLM to start
Write-Host "⏳ Waiting for LiteLLM proxy to start..." -ForegroundColor Blue
Start-Sleep -Seconds 8

# Check if LiteLLM is running using curl.exe (not the PowerShell alias)
try {
    $response = curl.exe -s http://localhost:4000/health 2>$null
    if ($LASTEXITCODE -eq 0 -and $response) {
        Write-Host "✅ LiteLLM proxy is running" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Error: LiteLLM proxy failed to start or is not responding" -ForegroundColor Red
        Write-Host "   Check the job output:" -ForegroundColor Yellow
        Receive-Job -Name "LiteLLM-Proxy" -ErrorAction SilentlyContinue | Select-Object -Last 5
        Cleanup-Jobs
        exit 1
    }
}
catch {
    Write-Host "❌ Error: Cannot connect to LiteLLM proxy" -ForegroundColor Red
    Write-Host "   Make sure curl.exe is available and the proxy started correctly" -ForegroundColor Yellow
    Cleanup-Jobs
    exit 1
}

# Start Astra backend in background job
Write-Host "🧠 Starting Astra backend..." -ForegroundColor Blue

$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD\..\backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} -Name "Astra-Backend"

# Wait for Astra backend to start
Write-Host "⏳ Waiting for Astra backend to start..." -ForegroundColor Blue
Start-Sleep -Seconds 12

# Check if Astra backend is running using curl.exe
try {
    $response = curl.exe -s http://localhost:8000/health 2>$null
    if ($LASTEXITCODE -eq 0 -and $response) {
        Write-Host "✅ Astra backend is running" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Error: Astra backend failed to start" -ForegroundColor Red
        Write-Host "   Check the job output:" -ForegroundColor Yellow
        Receive-Job -Name "Astra-Backend" -ErrorAction SilentlyContinue | Select-Object -Last 5
        Cleanup-Jobs
        exit 1
    }
}
catch {
    Write-Host "❌ Error: Cannot connect to Astra backend" -ForegroundColor Red
    Cleanup-Jobs
    exit 1
}

# Display service URLs and status
Write-Host ""
Write-Host "🎉 Astra Engine is ready!" -ForegroundColor Green
Write-Host "📍 Astra Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📍 LiteLLM Proxy: http://localhost:4000" -ForegroundColor Cyan
Write-Host "📍 Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "📍 Gateway Health: http://localhost:8000/gateway/health" -ForegroundColor Cyan
Write-Host "📍 Admin UI: http://localhost:4000/ui" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Monitoring:" -ForegroundColor Yellow
Write-Host "   - Check job status: Get-Job" -ForegroundColor Gray
Write-Host "   - View proxy logs: Receive-Job -Name 'LiteLLM-Proxy' -Keep" -ForegroundColor Gray
Write-Host "   - View backend logs: Receive-Job -Name 'Astra-Backend' -Keep" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

# Keep the script running and monitor jobs
try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check if jobs are still running
        $proxyStatus = Get-Job -Name "LiteLLM-Proxy" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty State
        $backendStatus = Get-Job -Name "Astra-Backend" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty State
        
        if ($proxyStatus -ne "Running") {
            Write-Host "⚠️  LiteLLM proxy has stopped!" -ForegroundColor Red
            Write-Host "   Last output:" -ForegroundColor Yellow
            Receive-Job -Name "LiteLLM-Proxy" -ErrorAction SilentlyContinue | Select-Object -Last 3
            break
        }
        
        if ($backendStatus -ne "Running") {
            Write-Host "⚠️  Astra backend has stopped!" -ForegroundColor Red
            Write-Host "   Last output:" -ForegroundColor Yellow
            Receive-Job -Name "Astra-Backend" -ErrorAction SilentlyContinue | Select-Object -Last 3
            break
        }
    }
}
catch [System.Management.Automation.HaltCommandException] {
    # User pressed Ctrl+C
    Write-Host "`nStopping services..." -ForegroundColor Yellow
}
finally {
    Cleanup-Jobs
}
