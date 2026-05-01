# Astra Engine Quick Start Guide

## Current Status
✅ Backend is starting on http://localhost:8000  
⚠️ API Keys need to be configured  

## Step 1: Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your actual API keys:
```
# LiteLLM Gateway Configuration
LITELLM_MASTER_KEY=your_secure_master_key_here
LITELLM_DATABASE_URL=sqlite:///litellm.db

# Primary AI Provider - Google Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Fallback AI Provider - Hugging Face
HUGGINGFACE_TOKEN=your_huggingface_token_here

# Database Configuration
NEO4J_URI=neo4j+s://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# Search API
TAVILY_API_KEY=your_tavily_api_key_here

# Hugging Face Token for embeddings
HF_TOKEN=your_huggingface_token_here
```

## Step 2: Start Services

### Option A: Simple Backend Only (Current)
The backend is already running on http://localhost:8000

### Option B: Full Gateway Setup
1. Stop current backend (Ctrl+C in the terminal)
2. Run with LiteLLM proxy:
```bash
# Windows PowerShell
.\start_astra_simple.ps1

# Or Linux/Mac/WSL
./start_astra.sh
```

## Step 3: Verify Services

Check the health endpoints:
- **Backend Health**: http://localhost:8000/health
- **Gateway Health**: http://localhost:8000/gateway/health (if gateway running)
- **LiteLLM Proxy**: http://localhost:4000/health (if proxy running)

## Step 4: Test Research

Once services are running, test with:
- **Query**: "air pollution in delhi"
- **Expected**: Research processing with automatic fallback if Gemini fails

## Troubleshooting

### API Key Issues
- Ensure GOOGLE_API_KEY is set for Gemini
- Ensure HUGGINGFACE_TOKEN is set for Mistral fallback
- Check Google Cloud Console for API key restrictions

### Port Conflicts
- If port 8000 is busy: Change to `--port 8001`
- If port 4000 is busy: Change to `--port 4001`

### Windows Issues
- Use PowerShell for `.ps1` scripts
- Use Git Bash for `.sh` scripts
- Avoid PowerShell curl alias (use curl.exe)

## Next Steps

1. Configure your `.env` file with real API keys
2. Restart the backend to load the new environment
3. Test the research functionality
4. Monitor the LiteLLM Admin UI (if proxy running): http://localhost:4000/ui
