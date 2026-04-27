import uvicorn
import os
import json
from crewai import Task, Crew, Process
from langchain_groq import ChatGroq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Absolute imports based on your backend/app structure
from app.crew.agents import AstraCrew
from app.tools.graph_tool import neo4j_manager

load_dotenv()

app = FastAPI(title="Astra API")

# --- CORS CONFIGURATION ---
# In production, set FRONTEND_URL in Render to your Vercel domain
ALLOWED_ORIGINS = [
    os.getenv("FRONTEND_URL", "*"), 
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class ChatMessage(BaseModel):
    role: str
    content: str

class AnalysisRequest(BaseModel):
    topic: str
    history: list[ChatMessage] = []

# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    """Health check for Render monitoring."""
    return {"status": "healthy", "environment": "production"}

@app.get("/")
async def root():
    return {
        "status": "online", 
        "message": "Astra Intelligence Engine is Live",
        "version": "2026.1.0"
    }

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    """
    Primary streaming endpoint for real-time Agentic Research.
    """
    # Convert chat history into a readable string for the agents
    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in request.history])
    
    try:
        # AstraCrew handles the LLM initialization internally via ChatGroq
        astra = AstraCrew()
        
        def event_generator():
            # astra.run_crew_stream should handle the Crew logic and yield strings
            for log in astra.run_crew_stream(request.topic, history_str):
                if log.startswith("__FINAL_RESULT__:"):
                    final_result = log.replace("__FINAL_RESULT__:", "")
                    yield f"data: {json.dumps({'type': 'result', 'content': final_result})}\n\n"
                elif log.startswith("[ERROR]"):
                    yield f"data: {json.dumps({'type': 'error', 'content': log})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'content': log})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream Initialization Failed: {str(e)}")

@app.get("/graph_data")
async def get_graph_data():
    """Returns Knowledge Graph data for the D3.js frontend."""
    try:
        data = neo4j_manager.get_all_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_graph")
async def clear_graph():
    """Resets the Neo4j Cloud Instance."""
    try:
        with neo4j_manager.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        return {"status": "success", "message": "Knowledge graph reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RENDER ENTRY POINT ---
# Recommended Start Command for Render:
# gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT --timeout 120

if __name__ == "__main__":
    # Render provides the PORT via environment variable
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)