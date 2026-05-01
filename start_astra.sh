#!/bin/bash

# Astra Engine Startup Script
# Starts both LiteLLM proxy and Astra backend simultaneously

echo "🚀 Starting Astra Engine with AI Gateway..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please copy .env.example to .env and configure your API keys."
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start LiteLLM proxy in background
echo "🔧 Starting LiteLLM proxy on port 4000..."
cd backend
litellm --config config.yaml --port 4000 &
LITELLM_PID=$!

# Wait for LiteLLM to start
echo "⏳ Waiting for LiteLLM proxy to start..."
sleep 5

# Check if LiteLLM is running
if ! curl -s http://localhost:4000/health > /dev/null; then
    echo "❌ Error: LiteLLM proxy failed to start"
    kill $LITELLM_PID
    exit 1
fi

echo "✅ LiteLLM proxy is running"

# Start Astra backend in background
echo "🧠 Starting Astra backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
ASTRA_PID=$!

# Wait for Astra backend to start
echo "⏳ Waiting for Astra backend to start..."
sleep 10

# Check if Astra backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Error: Astra backend failed to start"
    kill $LITELLM_PID $ASTRA_PID
    exit 1
fi

echo "✅ Astra backend is running"

# Display service URLs
echo ""
echo "🎉 Astra Engine is ready!"
echo "📍 Astra Backend: http://localhost:8000"
echo "📍 LiteLLM Proxy: http://localhost:4000"
echo "📍 Health Check: http://localhost:8000/health"
echo "📍 Gateway Health: http://localhost:8000/gateway/health"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for background processes
wait
