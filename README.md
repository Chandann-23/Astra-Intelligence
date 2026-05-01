---
title: Astra Backend
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
# Add the line below to point to your backend folder
dockerfile: backend/Dockerfile 
pinned: false
---
Astra Intelligence: Advanced Agentic Research Framework
Astra Intelligence is a production-level agentic research system designed to move beyond simple LLM chat interfaces. It utilizes a multi-agent orchestration layer to conduct deep web research, synthesize complex information, and persist structured insights into a graph database for real-time visualization.

🚀 Key Features
AI Gateway Architecture: Uses LiteLLM to create a unified "astra-brain" model with automatic fallback between Gemini and Mistral, eliminating 404 errors.

Multi-Agent Orchestration: Utilizes LangGraph to manage specialized agents (researcher, critic, storage) that collaborate to fulfill complex research goals.

High-Memory Backend: Hosted on Hugging Face Spaces with a 16GB RAM Docker environment to handle heavy agentic workloads and long-running research sequences.

Knowledge Graph Persistence: Automatically extracts entities and relationships from research data and stores them in Neo4j, providing a structured "memory" for the system.

## Quick Start (Local Development)

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Start Astra Engine**
   ```bash
   # Windows
   start_astra.bat
   
   # Linux/Mac
   chmod +x start_astra.sh
   ./start_astra.sh
   ```

4. **Access Services**
   - Astra Backend: http://localhost:8000
   - LiteLLM Proxy: http://localhost:4000
   - Health Check: http://localhost:8000/health
   - Gateway Health: http://localhost:8000/gateway/health

## AI Gateway Configuration

The `config.yaml` file defines the AI Gateway routing:
- **Primary Model**: `gemini/gemini-1.5-flash` with v1 endpoint
- **Fallback Model**: `mistral/mistral-nemo` for reliability
- **Unified Alias**: `astra-brain` used throughout the application

This architecture automatically handles 404 errors by retrying with the fallback provider.

## Monitoring & Administration

### LiteLLM Admin Dashboard
Access the built-in monitoring dashboard to track request latency, error rates, and fallback triggers:

- **Local**: http://localhost:4000/ui
- **Authentication**: Use your `LITELLM_MASTER_KEY` from `.env`
- **Features**: 
  - Real-time request monitoring
  - Error rate tracking
  - Model usage statistics
  - Fallback trigger visibility

### Health Endpoints
- **Main Health**: http://localhost:8000/health
- **Gateway Health**: http://localhost:8000/gateway/health
- **Proxy Health**: http://localhost:4000/health

### Testing the Gateway
Run the comprehensive test suite to verify fallback functionality:
```bash
cd backend
python test_gateway.py
```

This script tests:
- Automatic fallback when primary model fails
- Direct model access
- Gateway health and responsiveness

Real-time Streaming UI: Features a custom-built dashboard with a Strategy Stream for observing agent "thoughts" and a live Knowledge Graph visualizer.

Automated CI/CD: Integrated GitHub Actions pipeline that automatically syncs code to Hugging Face, ensuring seamless production deployments.

🏗️ System Architecture
The project is structured as a unified monorepo for maximum developer efficiency:

/frontend: A Next.js/React application optimized for real-time Server-Sent Events (SSE) to stream agent logs.

/backend: A FastAPI-driven Docker container orchestrating LLM calls via LiteLLM and tool execution.

🛠️ Tech Stack
LLM: Llama 3.3 (via Groq) for high-speed, low-latency reasoning.

Agentic Framework: CrewAI for task management and agent collaboration.

Database: Neo4j (Graph Database) for relational knowledge persistence.

Backend: FastAPI & Docker (Hosted on Hugging Face).

Frontend: Next.js (Hosted on Vercel).

Search API: Tavily for optimized AI search results.

🔧 Installation & Local Setup
Prerequisites
Python 3.12+

Docker (Optional)

API Keys for Groq, Tavily, and Neo4j

Setup Steps
Clone the repository:
git clone [https://github.com/Chandann-23/Astra-Intelligence.git](https://github.com/Chandann-23/Astra-Intelligence.git)

## Setup
1. **Database**: Run `docker-compose up -d`
2. **Backend**:
   - `cd backend`
   - `pip install -r requirements.txt`
   - Configure `.env` with required API keys:
     - `GROQ_API_KEY`
     - `TAVILY_API_KEY`
     - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
     - `GEMINI_API_KEY` (for Gemini Pro integration)
3. **Frontend**:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

Install dependencies: npm install.

Run the development server: npm run dev.

📈 Future Roadmap
Autonomous System Repair: Integration of Core-SRE features for self-healing backend logic.

Cross-Domain Mastery: Extending agents to handle specialized domains like financial analysis and code auditing.

Hybrid Memory: Integrating vector search alongside the existing Knowledge Graph for a complete RAG experience.