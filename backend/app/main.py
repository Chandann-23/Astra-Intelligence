import uvicorn
import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables
load_dotenv()
print('🚀 ASTRA ENGINE STARTING IN PRODUCTION MODE (V2)...')

# Optimized import to prevent "Warming Up" phase delays
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
    """Health check reflecting V2 status"""
    try:
        from app.tools.graph_tool import neo4j_manager
        return {
            "status": "online",
            "model": "Astra V2 LLM Backend",
            "services": {
                "neo4j": "connected" if neo4j_manager else "disconnected"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    print(f'DEBUG: Request for: {request.topic}')
    try:
        queue = asyncio.Queue()
        initial_state = {
            "query": request.topic, 
            "research_output": "", 
            "critique": "", 
            "revision_count": 0, 
            "storage_result": "",
            "queue": queue
        }
        
        async def run_graph(q, state):
            last_seen_state = state.copy()
            try:
                async for chunk in app_graph.astream(state):
                    for node_name, node_state in chunk.items():
                        # We don't want to copy the queue object over to last_seen_state, but it's fine if we do
                        last_seen_state.update(node_state)
                        
                        status_map = {
                            "researcher": {
                                "status": "researching", 
                                "message": "Lead Researcher generating report...", 
                                "node": "researcher",
                                "trace": "Researcher analyzing query and generating comprehensive research report."
                            },
                            "critic": {
                                "status": "critiquing", 
                                "message": "Senior Critic reviewing findings...", 
                                "node": "critic",
                                "trace": "Critic evaluating research quality and providing feedback for improvement."
                            },
                            "storage": {
                                "status": "storing", 
                                "message": "Archiving to Neo4j Knowledge Graph...", 
                                "node": "storage",
                                "trace": "Storage agent persisting research results to Neo4j database."
                            }
                        }
                        
                        status_update = status_map.get(node_name, {"status": "processing", "message": f"Executing {node_name}...", "node": node_name})
                        status_update["trace"] = f"Agent {node_name.upper()} is active: processing core logic..."
                        
                        # We don't yield partial_result here because it's streamed directly from invoke_llm!
                        # We just send the node completion event
                        await q.put(status_update)
                
                final_response = {
                    "status": "completed",
                    "message": "Research analysis completed successfully",
                    "result": last_seen_state.get("research_output", ""),
                    "storage_result": last_seen_state.get("storage_result", ""),
                    "node": "end"
                }
                await q.put(final_response)
            except Exception as graph_error:
                await q.put({'status': 'error', 'message': str(graph_error), 'node': 'end'})
        
        # Launch background task for graph execution
        task = asyncio.create_task(run_graph(queue, initial_state))
        
        async def generate_stream():
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Astra Warming Up...', 'node': 'start'})}\n\n"
            
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("node") == "end":
                    break
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)