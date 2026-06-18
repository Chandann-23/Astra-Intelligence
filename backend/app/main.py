import uvicorn
import os
import json
import asyncio
import re
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
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
from app.crew.agents import app_graph, invoke_llm

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
@app.head("/health")
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

def is_conversational_query(topic: str) -> bool:
    # Standardize topic
    t = topic.lower().strip().strip("?!.,- ")
    
    # Exact match common words
    greetings = {
        "hi", "hello", "hey", "greetings", "howdy", "yo", "sup", "hola",
        "good morning", "good afternoon", "good evening", "good day",
        "hey there", "hi there", "hello there", "hello astra", "hey astra",
        "hey bro", "whats up", "what's up", "hey bro what's up", "hey bro whats up"
    }
    if t in greetings:
        return True
        
    # Common short small talk phrases
    small_talk = [
        "how are you", "how's it going", "how is it going", "how are you doing",
        "what's up", "whats up", "how have you been", "who are you", 
        "what is your name", "what do you do", "tell me about yourself",
        "nice to meet you", "good to see you", "hey bro", "what can you do"
    ]
    for phrase in small_talk:
        if phrase in t:
            # Ensure it's not a longer research question containing the phrase
            if len(t.split()) <= 6:
                return True
                
    # Match pattern "hey/hi/hello [how are you / what's up / etc]"
    # Regex to match simple greetings with or without punctuation
    pattern = r"^(hi|hello|hey|yo|sup|greetings|hola)\b.*"
    if re.match(pattern, t):
        # If the greeting is part of a longer sentence, only classify as conversational
        # if the total word count is small (<= 7 words)
        if len(t.split()) <= 7:
            return True
            
    return False

@app.post("/stream")
async def stream_analysis(request: AnalysisRequest, http_request: Request):
    # Fallback: extract user_id from Authorization header if not in body
    effective_user_id = request.user_id
    if not effective_user_id:
        auth_header = http_request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            effective_user_id = auth_header.removeprefix("Bearer ").strip() or None
    
    print(f'DEBUG: Request for: {request.topic} | RAG Mode: {request.rag_mode} | Chat ID: {request.chat_id} | User ID: {effective_user_id}')
    
    # Database persistence is now handled directly by the frontend to ensure robust session/CORS handling.
    pass

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
                
                raw_result = last_seen_state.get("research_output", "")
                # Safety net: strip any leftover ACTION: blocks that leaked into the final answer
                import re as _re
                clean_result = _re.sub(
                    r'ACTION:\s*(?:WEB_SEARCH|CODE_EXECUTE)[\s\S]*?(?=\n\n|\Z)',
                    '',
                    raw_result,
                    flags=_re.DOTALL
                ).strip()
                
                final_response = {
                    "status": "completed",
                    "message": "Research analysis completed successfully",
                    "result": clean_result,
                    "storage_result": last_seen_state.get("storage_result", ""),
                    "node": "end"
                }
                
                # Astra message persistence is now handled by the frontend.
                pass
                        
                await q.put(final_response)
            except Exception as graph_error:
                await q.put({'status': 'error', 'message': str(graph_error), 'node': 'end'})
        
        async def run_conversational(q):
            try:
                # Inform frontend that processing has started
                await q.put({"status": "processing", "message": "Astra is typing...", "node": "researcher"})
                
                # Format system prompt for casual conversation / human interaction
                system_prompt = (
                    "You are Astra, a highly intelligent, friendly, and human-like AI assistant. "
                    "The user is engaging in casual conversation, small talk, or greeting you. "
                    "Respond in a very natural, warm, friendly, and human-like tone (e.g. dynamic greeting, "
                    "matching their vibe/slang if appropriate). Keep your response relatively brief (1-3 sentences) "
                    "and invite them to ask you any question, research query, or analysis topic."
                )
                
                # Gather recent history
                history_messages = []
                for msg in request.history[-6:]:
                    role = "assistant" if msg.get("role") == "astra" else "user"
                    content = msg.get("content", "")
                    if "System initialized" in content:
                        continue
                    if role == "assistant" and len(content) > 1500:
                        content = content[:1500] + "\n\n... [Previous response truncated]"
                    history_messages.append({"role": role, "content": content})
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    *history_messages,
                    {"role": "user", "content": request.topic}
                ]
                
                # Call invoke_llm to stream results
                response = await invoke_llm(messages, q, request.llm_provider)
                
                final_response = {
                    "status": "completed",
                    "message": "Chat response completed",
                    "result": response.strip(),
                    "node": "end"
                }
                await q.put(final_response)
            except Exception as graph_error:
                await q.put({'status': 'error', 'message': str(graph_error), 'node': 'end'})

        # Launch background task for execution: conversational router
        if is_conversational_query(request.topic):
            task = asyncio.create_task(run_conversational(queue))
        else:
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