import uvicorn
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
def health(): return {"status": "online"}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    try:
        astra = AstraCrew()
        return StreamingResponse(
            astra.run_crew_stream(request.topic, str(request.history)), 
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)