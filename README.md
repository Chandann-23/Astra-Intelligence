# Astra

A production-ready Full-Stack Agentic AI project.

## Architecture
- **Backend**: FastAPI with CrewAI
- **Frontend**: Next.js 15 (TypeScript, Tailwind CSS)
- **Database**: Neo4j (Graph Database)
- **LLM**: Llama 3.3 via Groq

## Setup
1. **Database**: Run `docker-compose up -d`
2. **Backend**:
   - `cd backend`
   - `pip install -r requirements.txt`
   - Configure `.env`
3. **Frontend**:
   - `cd frontend`
   - `npm install`
   - `npm run dev`
.