#!/usr/bin/env python3
"""
Clean FastAPI application to fix request handling issues
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()
print('🚀 ASTRA ENGINE STARTING...')
print(f'DEBUG: API KEY EXISTS: {bool(os.getenv("GOOGLE_API_KEY"))}')

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

# Simplified CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    topic: str
    history: list = []

@app.get("/")
def root():
    return {"status": "ok", "message": "Astra Engine is running"}

@app.get("/health")
def health():
    try:
        from app.tools.graph_tool import neo4j_manager
        import requests
        
        # Check LiteLLM proxy health (only in local development)
        is_local = os.getenv("ENVIRONMENT") == "local" or os.getenv("OPENAI_BASE_URL", "").startswith("http://localhost")
        gateway_status = "direct_provider" if not is_local else "down"
        
        if is_local:
            try:
                response = requests.get("http://localhost:48583/health", timeout=5)
                if response.status_code == 200:
                    gateway_status = "proxy_online"
                else:
                    gateway_status = "proxy_down"
            except:
                gateway_status = "proxy_down"
        
        # Check API keys
        google_key = os.environ.get("GOOGLE_API_KEY")
        hf_token = os.environ.get("HUGGINGFACE_TOKEN")
        
        return {
            "status": "online",
            "services": {
                "neo4j": "connected" if (hasattr(neo4j_manager, 'driver') and neo4j_manager.driver) else "disconnected",
                "gateway": gateway_status,
                "google": "configured" if google_key else "missing",
                "huggingface": "configured" if hf_token else "missing",
                "tavily": "configured" if os.environ.get("TAVILY_API_KEY") else "missing"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/gateway/health")
def gateway_health():
    """Specific health check for LiteLLM proxy or direct provider"""
    try:
        import requests
        
        # In production, use direct provider access
        if os.getenv("ENVIRONMENT") != "local" and not os.getenv("OPENAI_BASE_URL", "").startswith("http://localhost"):
            return {"status": "online", "gateway": "direct_provider"}
        
        # Local development - check LiteLLM proxy
        response = requests.get("http://localhost:48583/health", timeout=5)
        if response.status_code == 200:
            return {"status": "online", "gateway": "proxy_healthy"}
        else:
            return {"status": "error", "message": "Gateway returned non-200 status"}
    except Exception as e:
        return {"status": "GATEWAY_DOWN", "message": f"Cannot reach LiteLLM proxy: {str(e)}"}

@app.get("/test")
def test_endpoint():
    """Minimal test endpoint to isolate request handling issues"""
    return {"status": "ok", "message": "Test endpoint working"}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    print(f'DEBUG: Received research request for: {request.topic}')
    try:
        # Initialize state for LangGraph
        initial_state = {
            "query": request.topic,
            "research_output": "",
            "critique": "",
            "revision_count": 0,
            "storage_result": ""
        }
        
        async def generate_stream():
            # Send immediate heartbeat
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Astra Engine warming up...', 'node': 'start'})}\n\n"
            
            last_seen_state = initial_state
            
            try:
                # Import and use the graph
                from app.crew.agents import app_graph
                
                async for chunk in app_graph.astream(initial_state):
                    # Stream each node's output
                    for node_name, node_output in chunk.items():
                        if node_output != last_seen_state:
                            # Send node completion
                            yield f"data: {json.dumps({'status': 'node_complete', 'node': node_name, 'output': node_output})}\n\n"
                            last_seen_state = node_output
                
                # Send final completion
                yield f"data: {json.dumps({'status': 'complete', 'message': 'Research completed successfully'})}\n\n"
                
            except Exception as e:
                print(f"Streaming error: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': f'Research failed: {str(e)}'})}\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
        
    except Exception as e:
        print(f"Stream analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, http="h11")
