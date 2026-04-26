import uvicorn
import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from app.crew.agents import AstraCrew
from app.tools.graph_tool import neo4j_manager

load_dotenv()

app = FastAPI(title="Astra API")

# CORS setup for Vercel + Local Dev
ALLOWED_ORIGINS = [
    os.getenv("FRONTEND_URL", "*"), # Set FRONTEND_URL in Render to your Vercel URL
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Render deployment.
    """
    return {"status": "healthy"}

# Request model for better validation
class ChatMessage(BaseModel):
    role: str
    content: str

class AnalysisRequest(BaseModel):
    topic: str
    history: list[ChatMessage] = []

@app.get("/")
async def root():
    return {"status": "online", "message": "Astra Intelligence Engine is Live"}

@app.post("/analyze")
async def analyze_topic(request: AnalysisRequest):
    """
    Standard endpoint (Non-streaming)
    """
    try:
        from app.crew.agents import AstraCrew as OldAstraCrew
        # Note: We'd need to keep the old kickoff or adapt this
        # For simplicity in this architectural shift, we recommend using /stream
        raise HTTPException(status_code=400, detail="Please use the /stream endpoint for real-time analysis.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    """
    Streaming endpoint using POST to accept chat history
    """
    # Convert history list to a string format for the agents
    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in request.history])
    
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

@app.get("/graph_data")
async def get_graph_data():
    """
    Returns the full knowledge graph in D3-compatible format.
    """
    try:
        data = neo4j_manager.get_all_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_graph")
async def clear_graph():
    """
    Clears all nodes and relationships from the Neo4j graph.
    """
    try:
        with neo4j_manager.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        return {"status": "success", "message": "Knowledge graph reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
