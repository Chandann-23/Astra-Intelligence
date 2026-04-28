import uvicorn
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.crew.agents import AstraCrew

app = FastAPI(title="Astra API")

# NUCLEAR CORS: This is why the code is shorter. 
# It replaces the long list of origins and fixes the "Blocked by CORS" error.
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
async def health():
    return {"status": "online"}

@app.get("/")
async def root():
    return {"message": "Astra Engine Live"}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    try:
        # We initialize the crew here
        astra = AstraCrew()
        # Convert the history list to a string for the agents to read
        history_str = str(request.history)
        
        return StreamingResponse(
            astra.run_crew_stream(request.topic, history_str), 
            media_type="text/event-stream"
        )
    except Exception as e:
        # This will catch any startup errors and show them in your Vercel console
        print(f"Detailed Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Railway sets the PORT env variable automatically
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)