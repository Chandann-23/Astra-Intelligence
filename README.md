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
## Astra Intelligence: Advanced Agentic Research Framework ##
**Astra Intelligence** is a high-performance, multi-agent research engine designed to bridge the gap between real-time web data and persistent knowledge graphs. Built as a second-year AIML project at Presidency University, it utilizes a sophisticated Neural-Symbolic approach to provide deep, verified insights into complex queries.

# 🚀 Live Demo #
[Explore Astra Intelligence](https://astra-intelligence-phi.vercel.app/)

# 🛠️ Core Technology Stack #
*Brain*: Llama-3.3-70B via SambaNova/Together AI for lightning-fast agentic reasoning.

*Orchestration*: LangGraph-powered state machines to manage Researcher-Critic cycles with built-in recursion safety.

*Real-time Intelligence*: Tavily Search API for fetching authoritative web sources.

*Persistent Memory*: Neo4j Graph Database for structured knowledge retrieval and agent state management.

*Frontend*: Next.js 16 (Turbopack) featuring a Gemini-inspired UI with real-time "push-up" auto-scrolling.

# 🏗️ Key Engineering Features #
*Agentic Circuit Breaker*: Custom logic to prevent infinite agent loops (Recursion Limit safety).

*Rate Limit Resilience*: Optimized with strategic delays and retry logic to maintain 100% uptime on free-tier APIs.

*Dual-Source RAG*: Simultaneously pulls from live web streams and persistent graph memory.

*Optimized Deployment*: Built with industrial IoT standards for telemetry and thermal monitoring simulations.

# 💻 Local Deployment for Recruiters #
To run the Astra Engine on your local machine:

# 1. Prerequisites #
Python 3.10+

Node.js 18+

Neo4j instance (Local or AuraDB)

# 2. Environment Setup #
Create a .env file in the root directory based on .env.example:

Code snippet
SAMBANOVA_API_KEY=your_key
TAVILY_API_KEY=your_key
NEO4J_URI=your_uri
NEO4J_PASSWORD=your_password
# 3. Quick Start (One-Click) #
Use the provided automation scripts in the /scripts folder:

Windows (PowerShell): ./scripts/start_astra.ps1

Windows (CMD): ./scripts/start_astra.bat

Linux/macOS: bash ./scripts/start_astra.sh

# ☁️ Hugging Face Integration #
This repository is pre-configured for Hugging Face Spaces.

*Requirements:* Ensure requirements.txt and Dockerfile remain in the root for the Python backend.

*Hardware:* Optimized to run on CPU Basic or T4 Small instances through efficient import handling.

# 📄 Documentation & SRE #
Detailed engineering logs and reliability audits can be found in the /docs folder:

*PRODUCTION_AUDIT.md*: Analysis of system performance and bottleneck fixes.

*SRE_CHECKLIST.md*: Reliability protocols used for deployment.