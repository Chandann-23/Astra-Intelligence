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
print(f'DEBUG: API KEY EXISTS: {bool(os.getenv("GOOGLE_API_KEY"))}')

# We skip the validate_proxy_connection() function entirely for Hugging Face
from app.crew.agents import app_graph

app = FastAPI()

# Standard CORS for Production
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
    """Production-only health check without localhost pings"""
    try:
        from app.tools.graph_tool import neo4j_manager
        return {
            "status": "online",
            "environment": "production",
            "services": {
                "neo4j": "connected" if (hasattr(neo4j_manager, 'driver') and neo4j_manager.driver) else "disconnected",
                "gateway": "direct_provider", # Hardcoded to bypass localhost errors
                "google": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
                "huggingface": "configured" if os.getenv("HUGGINGFACE_TOKEN") else "missing"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/gateway/health")
def gateway_health():
    """Bypasses local check for production stability"""
    return {"status": "online", "gateway": "direct_provider_active"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "Astra Cloud Engine is active"}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    print(f'DEBUG: Received research request for: {request.topic}')
    try:
        initial_state = {
            "query": request.topic,
            "research_output": "",
            "critique": "",
            "revision_count": 0,
            "storage_result": ""
        }
        
        async def generate_stream():
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Astra Engine warming up...', 'node': 'start'})}\n\n"
            last_seen_state = initial_state
            
            try:
                async for chunk in app_graph.astream(initial_state):
                    for node_name, node_state in chunk.items():
                        last_seen_state.update(node_state)
                        
                        status_map = {
                            "researcher": {"status": "researching", "message": "Lead Researcher generating report...", "node": "researcher"},
                            "critic": {"status": "critiquing", "message": "Senior Critic reviewing findings...", "node": "critic"},
                            "storage": {"status": "storing", "message": "Archiving to Neo4j Knowledge Graph...", "node": "storage"}
                        }
                        
                        status_update = status_map.get(node_name, {"status": "processing", "message": f"Executing {node_name}...", "node": node_name})
                        
                        if "research_output" in node_state:
                            content = node_state["research_output"]
                            status_update["partial_result"] = content[:500] + "..." if len(content) > 500 else content
                        
                        yield f"data: {json.dumps(status_update)}\n\n"
                
                final_response = {
                    "status": "completed",
                    "message": "Research analysis completed successfully",
                    "result": last_seen_state.get("research_output", ""),
                    "storage_result": last_seen_state.get("storage_result", ""),
                    "node": "end"
                }
                yield f"data: {json.dumps(final_response)}\n\n"
                    
            except Exception as graph_error:
                print(f"GRAPH ERROR: {str(graph_error)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(graph_error), 'node': 'error'})}\n\n"
        
        return StreamingResponse(
            generate_stream(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no" 
            }
        )
    except Exception as e:
        print(f"SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    # We remove the "app.main:app" string and use the object directly for HF stability
    uvicorn.run(app, host="0.0.0.0", port=port)