import uvicorn
import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client, Client

# Load environment variables
load_dotenv()
print('🚀 ASTRA ENGINE STARTING IN PRODUCTION MODE (V2)...')

# Initialize Supabase client
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
supabase_client: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print('✅ Supabase Client Initialized')
else:
    print('⚠️ Supabase credentials missing. Database persistence disabled.')

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
    rag_mode: str = "general"
    chat_id: str = None
    user_id: str = None
    llm_provider: str = "gemini"
    developer_resume_mode: bool = False

@app.get("/")
def read_root():
    """Root endpoint for Hugging Face Spaces iframe"""
    return {
        "app": "Astra Intelligence Engine V2",
        "status": "operational",
        "endpoints": ["/health", "/stream", "/upload"]
    }

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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload notes or PDF to local Neo4j RAG"""
    try:
        from app.tools.graph_tool import neo4j_manager
        content = await file.read()
        text = ""
        
        if file.filename.lower().endswith(".pdf"):
            import io
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(content))
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        else:
            text = content.decode("utf-8")
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="File is empty or text could not be extracted.")
            
        success = await neo4j_manager.ingest_document(file.filename, text)
        if success:
            return {"status": "success", "message": f"Successfully ingested {file.filename} into NotebookLM index."}
        else:
            raise HTTPException(status_code=500, detail="Ingestion failed. Database offline.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    print(f'DEBUG: Request for: {request.topic} | RAG Mode: {request.rag_mode} | Chat ID: {request.chat_id}')
    
    # 1. Asynchronously persist the User message
    if supabase_client and request.chat_id and request.user_id:
        try:
            # Upsert chat metadata
            chat_title = request.topic[:40] + ('...' if len(request.topic) > 40 else '') if not request.history else None
            
            # Note: For Supabase realtime to work best, we check if title exists (new chat)
            if chat_title:
                supabase_client.table("chats").upsert({
                    "id": request.chat_id,
                    "title": chat_title,
                    "user_id": request.user_id,
                }).execute()
            else:
                supabase_client.table("chats").update({
                    "id": request.chat_id # Dummy update just to touch the table, usually updated_at auto-triggers
                }).eq("id", request.chat_id).execute()
                
            # Insert User Message
            supabase_client.table("messages").insert({
                "chat_id": request.chat_id,
                "role": "user",
                "content": request.topic,
                "type": "text"
            }).execute()
        except Exception as e:
            print(f"Database sync error (user msg): {e}")

    try:
        queue = asyncio.Queue()
        initial_state = {
            "query": request.topic, 
            "history": request.history,
            "research_output": "", 
            "critique": "", 
            "revision_count": 0, 
            "storage_result": "",
            "queue": queue,
            "rag_mode": request.rag_mode,
            "llm_provider": request.llm_provider,
            "developer_resume_mode": request.developer_resume_mode,
            "tool_loop_count": 0
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
                            "searcher": {
                                "status": "searching",
                                "message": "Search Agent querying live web...",
                                "node": "searcher",
                                "trace": "Search Agent executing Tavily web queries to pull live data."
                            },
                            "coder": {
                                "status": "executing",
                                "message": "Python Coder executing code block...",
                                "node": "coder",
                                "trace": "Coder Agent running Python code inside secure sandbox."
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
                
                # 2. Asynchronously persist the Astra message
                if supabase_client and request.chat_id:
                    try:
                        supabase_client.table("messages").insert({
                            "chat_id": request.chat_id,
                            "role": "astra",
                            "content": last_seen_state.get("research_output", ""),
                            "type": "analysis"
                        }).execute()
                    except Exception as e:
                        print(f"Database sync error (astra msg): {e}")
                        
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