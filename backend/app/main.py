import uvicorn
print('🚀 ASTRA ENGINE STARTING...')

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.crew.agents import AstraCrew

app = FastAPI()

# Allow EVERYTHING to stop CORS headaches
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    topic: str
    history: list = []

@app.get("/health")
def health():
    try:
        # Check Neo4j connection
        from app.tools.graph_tool import neo4j_manager
        neo4j_status = "connected" if neo4j_manager.driver else "disconnected"
        
        # Check LLM initialization
        gemini_status = "configured" if os.environ.get("GEMINI_API_KEY") else "missing"
        
        return {
            "status": "online",
            "services": {
                "neo4j": neo4j_status,
                "gemini": gemini_status,
                "groq": "configured" if os.environ.get("GROQ_API_KEY") else "missing",
                "tavily": "configured" if os.environ.get("TAVILY_API_KEY") else "missing"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    try:
        astra = AstraCrew()
        return StreamingResponse(
            astra.run_crew_stream(request.topic, str(request.history)), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)