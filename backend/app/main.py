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

# We use absolute imports relative to the /backend folder
from app.crew.agents import AstraCrew
from app.tools.graph_tool import neo4j_manager

load_dotenv()

app = FastAPI(title="Astra API")

# --- CORS CONFIGURATION ---
# We fetch the frontend URL from environment variables to avoid hardcoding issues.
frontend_url = os.getenv("FRONTEND_URL", "https://astra-intelligence-phi.vercel.app")

origins = [
    "http://localhost:3000",
    frontend_url,
    "https://astra-intelligence-eta.vercel.app",
    "https://astra-intelligence-gamma.vercel.app",
    "https://astra-intelligence-phi.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in request.history])
    
    try:
        astra = AstraCrew()
        
        def event_generator():
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
    try:
        data = neo4j_manager.get_all_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_graph")
async def clear_graph():
    try:
        with neo4j_manager.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        return {"status": "success", "message": "Knowledge graph reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RAILWAY ENTRY POINT ---
if __name__ == "__main__":
    # We bind to 0.0.0.0 to allow external connections from Vercel
    port = int(os.environ.get("PORT", 8080))
    # Note: Use "app.main:app" because we are inside the /backend root
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)