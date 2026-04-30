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
from app.crew.agents import app_graph

app = FastAPI()

# Allow EVERYTHING to stop CORS headaches
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, # Changed to True for better cookie/session handling
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    topic: str
    history: list = []

@app.get("/health")
def health():
    try:
        from app.tools.graph_tool import neo4j_manager
        # Check Gemini API key for stable 8b integration
        gemini_key = os.environ.get("GOOGLE_API_KEY")
        
        return {
            "status": "online",
            "services": {
                "neo4j": "connected" if (hasattr(neo4j_manager, 'driver') and neo4j_manager.driver) else "disconnected",
                "gemini": "configured" if gemini_key else "missing",
                "tavily": "configured" if os.environ.get("TAVILY_API_KEY") else "missing"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
                # Use stream instead of astream if your graph isn't fully async, 
                # but astream is better for FastAPI.
                async for chunk in app_graph.astream(initial_state):
                    # LangGraph chunk format is {node_name: {updated_state_keys}}
                    for node_name, node_state in chunk.items():
                        # Update our tracker so we have the final result at the end
                        last_seen_state.update(node_state)
                        
                        status_map = {
                            "researcher": {"status": "researching", "message": "Lead Researcher generating report...", "node": "researcher"},
                            "critic": {"status": "critiquing", "message": "Senior Critic reviewing findings...", "node": "critic"},
                            "storage": {"status": "storing", "message": "Archiving to Neo4j Knowledge Graph...", "node": "storage"}
                        }
                        
                        status_update = status_map.get(node_name, {"status": "processing", "message": f"Executing {node_name}...", "node": node_name})
                        
                        # Add partial result if the researcher just finished
                        if "research_output" in node_state:
                            content = node_state["research_output"]
                            status_update["partial_result"] = content[:500] + "..." if len(content) > 500 else content
                        
                        yield f"data: {json.dumps(status_update)}\n\n"
                
                # FINAL PACKET: Send the total accumulated state
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
                "X-Accel-Buffering": "no" # Critical for Hugging Face/Nginx streaming
            }
        )
    except Exception as e:
        print(f"SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)