import uvicorn
import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables
load_dotenv()
print('🚀 ASTRA ENGINE STARTING IN PRODUCTION MODE...')
# FIXED: Checking for the key you actually use in production
print(f'DEBUG: HUGGINGFACE API KEY EXISTS: {bool(os.getenv("HUGGINGFACE_API_KEY"))}')

from app.crew.agents import app_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    topic: str
    history: list = []

@app.get("/health")
def health():
    """Health check reflecting GLM-5.1 status"""
    try:
        from app.tools.graph_tool import neo4j_manager
        hf_key = bool(os.getenv("HUGGINGFACE_API_KEY"))
        return {
            "status": "online",
            "model": "GLM-5.1 via Hugging Face",
            "services": {
                "neo4j": "connected" if (hasattr(neo4j_manager, 'driver') and neo4j_manager.driver) else "disconnected",
                "huggingface": "configured" if hf_key else "missing"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    print(f'DEBUG: Request for: {request.topic}')
    try:
        initial_state = {"query": request.topic, "research_output": "", "critique": "", "revision_count": 0, "storage_result": ""}
        
        async def generate_stream():
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Astra Warming Up...'})}\n\n"
            last_seen_state = initial_state
            try:
                async for chunk in app_graph.astream(initial_state):
                    for node_name, node_state in chunk.items():
                        last_seen_state.update(node_state)
                        yield f"data: {json.dumps({'status': 'processing', 'node': node_name})}\n\n"
                
                yield f"data: {json.dumps({'status': 'completed', 'result': last_seen_state.get('research_output', '')})}\n\n"
            except Exception as graph_error:
                yield f"data: {json.dumps({'status': 'error', 'message': str(graph_error)})}\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)