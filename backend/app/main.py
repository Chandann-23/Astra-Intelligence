import uvicorn
print('🚀 ASTRA ENGINE STARTING...')

import os
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
    print('DEBUG: Received research request')
    try:
        # Initialize state for LangGraph
        initial_state = {
            "query": request.topic,
            "research_output": "",
            "critique": "",
            "revision_count": 0
        }
        
        # Wrap LangGraph astream in async task
        async def generate_stream():
            # Send immediate heartbeat to keep stream alive
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Starting research...', 'node': 'start'})}\n\n"
            
            try:
                # Stream through LangGraph nodes
                async for chunk in app_graph.astream(initial_state):
                    # Extract node name and state from chunk
                    node_name = list(chunk.keys())[0] if chunk else "unknown"
                    current_state = chunk[node_name] if chunk else {}
                    
                    # Send status update for current node
                    status_map = {
                        "researcher": {"status": "researching", "message": "Analyzing query and generating report...", "node": "researcher"},
                        "critic": {"status": "critiquing", "message": "Reviewing report for depth and accuracy...", "node": "critic"},
                        "storage": {"status": "storing", "message": "Saving research to Neo4j...", "node": "storage"}
                    }
                    
                    status_update = status_map.get(node_name, {"status": "processing", "message": "Processing...", "node": node_name})
                    
                    # Include partial results if available
                    if current_state.get("research_output"):
                        status_update["partial_result"] = current_state["research_output"][:500] + "..." if len(current_state["research_output"]) > 500 else current_state["research_output"]
                    
                    yield f"data: {json.dumps(status_update)}\n\n"
                
                # Send final result
                final_state = chunk
                if final_state:
                    last_node = list(final_state.keys())[0] if final_state else "storage"
                    final_data = final_state[last_node] if final_state else {}
                    
                    final_response = {
                        "status": "completed",
                        "message": "Research analysis completed successfully",
                        "result": final_data.get("research_output", ""),
                        "storage_result": final_data.get("storage_result", ""),
                        "node": "end"
                    }
                    
                    yield f"data: {json.dumps(final_response)}\n\n"
                    
            except Exception as graph_error:
                # Graceful error handling to prevent stream crashes
                error_response = {
                    "status": "error", 
                    "message": str(graph_error),
                    "type": "graph_execution_error",
                    "node": "error"
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                return
        
        return StreamingResponse(
            generate_stream(), 
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