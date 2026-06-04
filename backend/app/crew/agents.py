import os
import json
import asyncio
import re
from typing import TypedDict, Annotated, Any
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from litellm.exceptions import RateLimitError

import litellm
from langgraph.graph import StateGraph, END
from app.tools.graph_tool import neo4j_manager
from app.tools.code_tool import execute_python_code

load_dotenv()

DEVELOPER_RESUME_CONTEXT = """
DEVELOPER PROFILE: CHANDAN (Senior AI & Full-Stack Software Engineer)
=====================================================================

OVERVIEW:
Chandan is a highly skilled Senior Software Engineer with deep expertise in AI agent orchestration, Large Language Models (LLMs), Graph RAG (Retrieval-Augmented Generation), and premium full-stack web applications. With a strong engineering background, Chandan focuses on building secure, resilient, SRE-compliant, and high-performance intelligent agent systems.

CORE TECHNICAL SKILLS:
* Languages: Python, TypeScript, JavaScript, SQL, HTML, CSS
* AI & Agents: LangGraph, LangChain, CrewAI, LiteLLM, OpenAI, Google Gemini API, Claude, Mistral AI, Hugging Face
* Database & RAG: Neo4j (Graph Database & Vector Indexing), PostgreSQL, Supabase (Vector Search, RLS, Auth, Database Functions)
* Frontend: Next.js (App Router), React 18/19, Zustand, Framer Motion, Tailwind CSS, Lucide React
* Infrastructure & SRE: Docker (isolated sandboxing), GitHub Actions (CI/CD), Tenacity (resilience retry patterns), Server-Sent Events (SSE) streaming

FEATURED PROJECTS:
1. Astra Intelligence V2 (This Application):
   * An advanced AI research engine with multi-agent orchestration (Lead Researcher, Coder, Critic, Storage Extractor).
   * Implemented a self-healing LLM router with automatic provider fallback handling (failsafe API failovers) to recover from rate-limiting (429 errors).
   * Developed a secure Python runtime execution sandbox utilizing Docker with local subprocess fallbacks for serverless environments.
   * Integrated Graph RAG linking semantic concepts using custom sentence-transformer embeddings saved to Neo4j.
2. Secure Agent Workspace:
   * A NotebookLM-style private workspace allowing users to securely index, search, and chat with their PDF/TXT knowledge base using Supabase vector embeddings.
3. High-Performance APIs:
   * Optimized token context windows by truncating history, saving up to 80% on token consumption while maintaining agent memory coherence.

WHY HIRE CHANDAN:
* AI Specialist: Expert in building actual functional multi-agent flows (not just single wrappers) using LangGraph state machines.
* Full-Stack Competence: Capable of building backend API architectures and immediately translating them into premium, glassmorphic UI web applications.
* Production Mindset: Prioritizes SRE standards—handling rate limits, backup fallbacks, memory constraints, and code sandboxing natively.
"""

class AgentState(TypedDict):
    query: str
    history: list
    research_output: str
    critique: str
    revision_count: int
    storage_result: str
    queue: Any # asyncio.Queue
    rag_mode: str
    execution_result: str
    llm_provider: str
    developer_resume_mode: bool

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def _invoke_llm_with_retry(messages, queue: asyncio.Queue = None, provider: str = "gemini") -> str:
    """Invoke LLM through LiteLLM with async streaming and tenacity backoff.
    
    Supported providers and verified models (as of June 2026):
    - gemini:    gemini/gemini-2.0-flash                        | Key: GEMINI_API_KEY    | 1,500 req/day free
    - groq:      groq/llama-3.3-70b-versatile                   | Key: GROQ_API_KEY      | 1,000 req/day, 100k TPD free
    - cerebras:  cerebras/gpt-oss-120b                          | Key: CEREBRAS_API_KEY  | 1M tokens/day free
    - sambanova: sambanova/Llama-4-Maverick-17B-128E-Instruct   | Key: SAMBANOVA_API_KEY | $5 free credits
    - mistral:   mistral/mistral-small-latest                   | Key: MISTRAL_API_KEY   | 1B tokens/month free (BEST free tier)
    """
    if provider == "sambanova":
        api_key = os.getenv("SAMBANOVA_API_KEY")
        model = "sambanova/Llama-4-Maverick-17B-128E-Instruct"  # Current featured free model
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        model = "groq/llama-3.3-70b-versatile"  # Verified active as of June 2026, 275+ tokens/sec
    elif provider == "cerebras":
        api_key = os.getenv("CEREBRAS_API_KEY")
        model = "cerebras/gpt-oss-120b"  # Llama 3.3 70B deprecated Feb 16 2026; GPT-OSS 120B is current flagship
    elif provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
        model = "mistral/mistral-small-latest"  # Best free tier: 1B tokens/month, 60 RPM, no credit card
    else:  # default: gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # Fallback to GOOGLE_API_KEY if GEMINI_API_KEY is not set
        model = "gemini/gemini-2.0-flash"      # gemini/ prefix routes via AI Studio (simple API key)
        
    if not api_key:
        return f"Error: API key for {provider} not found in environment."


    # Normalize prompt to messages list if a string is passed
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            api_key=api_key,
            stream=True
        )
        
        full_text = ""
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_text += content
                if queue:
                    await queue.put({"partial_result": content})
                    
        return full_text
        
    except RateLimitError as e:
        print("Rate limit hit, tenacity backing off...")
        raise e
    except Exception as e:
        error_msg = str(e)
        return f"Error: {error_msg}"

async def invoke_llm(messages, queue: asyncio.Queue = None, provider: str = "gemini") -> str:
    fallback_providers = ["gemini", "mistral", "groq", "cerebras", "sambanova"]
    
    if provider in fallback_providers:
        fallback_providers.remove(provider)
    fallback_providers.insert(0, provider)
    
    last_error = None
    accumulated_text = ""
    
    for idx, current_provider in enumerate(fallback_providers):
        # Pre-check API key availability to skip providers without keys
        if current_provider == "sambanova" and not os.getenv("SAMBANOVA_API_KEY"):
            continue
        elif current_provider == "groq" and not os.getenv("GROQ_API_KEY"):
            continue
        elif current_provider == "cerebras" and not os.getenv("CEREBRAS_API_KEY"):
            continue
        elif current_provider == "mistral" and not os.getenv("MISTRAL_API_KEY"):
            continue
        elif current_provider == "gemini" and not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            continue
            
        try:
            if idx > 0:
                if queue:
                    await queue.put({
                        "status": "provider_fallback",
                        "provider": current_provider,
                        "node": "researcher"
                    })
                    await queue.put({
                        "status": "processing",
                        "message": f"Switching to fallback provider: {current_provider.upper()} (quota exceeded/rate-limited on {provider.upper()})",
                        "node": "researcher"
                    })
                    
            result = await _invoke_llm_with_retry(messages, queue, current_provider)
            
            if isinstance(result, str) and result.startswith("Error:"):
                raise Exception(result)
                
            return result
            
        except Exception as e:
            last_error = str(e)
            print(f"Astra Fallback Engine: {current_provider.upper()} failed: {last_error}. Trying next provider...")
            continue
            
    return f"Error: All LLM providers exhausted. Last error: {last_error}"

async def researcher_node(state: AgentState) -> AgentState:
    if state.get("revision_count") is None:
        state["revision_count"] = 0
    else:
        state["revision_count"] += 1
        
    rag_mode = state.get("rag_mode", "general")
    execution_result = state.get("execution_result", "")
    
    if state.get("developer_resume_mode"):
        system_prompt = f"""
        You are a dedicated Recruiter Onboarding Agent for Chandan (the creator of Astra).
        Your mission is to answer questions about Chandan's background, projects, skills, and why he is a great hire.
        You must answer ONLY using the Developer Profile Context provided below.
        Be professional, persuasive, and directly highlight his technical expertise.
        
        Developer Profile Context:
        {DEVELOPER_RESUME_CONTEXT}
        """
        if state.get("queue"):
            await state["queue"].put({"status": "researching", "message": "Accessing Developer Profile Index...", "node": "researcher"})
    elif rag_mode == "strict_local":
        docs, reasoning = await neo4j_manager.document_vector_search(state.get('query', ''))
        context = "\n".join(docs)
        
        system_prompt = f"""
        You are a STRICT Local RAG assistant (NotebookLM mode). You must answer the user's query ONLY using the provided Context Notes below.
        DO NOT use any outside internet knowledge. If the answer is not contained in the Context Notes, say exactly: "I cannot find the answer in the provided notes."
        
        Context Notes:
        {context}
        """
        if state.get("queue"):
            await state["queue"].put({"status": "researching", "message": f"Scanning local documents: {reasoning}", "node": "researcher"})
    else:
        system_prompt = f"""
        You are an advanced AI research analyst with web search and code execution capabilities.
        
        - If you need to search the live web for real-time 2026 data or external facts, output EXACTLY this format:
        ACTION: WEB_SEARCH
        query = "<your search query here>"
        
        - If you need to run calculations or execute python code, output EXACTLY this format:
        ACTION: CODE_EXECUTE
        ```python
        <your python code here>
        ```
        - Otherwise, provide your detailed analysis.
        
        Code/Search Execution Result: {execution_result}
        Revision count: {state['revision_count']}
        """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Inject chat history (Optimized for Token Limits)
    raw_history = state.get("history", [])
    
    # 1. Keep only the last 6 messages (3 conversation turns) to prevent exploding context windows
    recent_history = raw_history[-6:]
    
    for msg in recent_history:
        role = "assistant" if msg.get("role") == "astra" else "user"
        content = msg.get("content", "")
        
        # Skip the hardcoded initialization message to save tokens
        if "System initialized" in content:
            continue
            
        # 2. Truncate massively long previous AI responses to save tokens.
        # We want the agent to remember the context, but we don't need to re-feed 4000 words.
        if role == "assistant" and len(content) > 1500:
            content = content[:1500] + "\n\n... [Previous response truncated by Memory Manager to save context window tokens]"
            
        messages.append({"role": role, "content": content})
        
    messages.append({"role": "user", "content": state.get("query", "")})
    
    response = await invoke_llm(messages, state.get("queue"), state.get("llm_provider", "gemini"))
    
    if "Error:" in response:
        state["research_output"] = response
        state["revision_count"] = 99 
    else:
        state["research_output"] = response
        
    return state

async def coder_node(state: AgentState) -> AgentState:
    """Extracts python code from researcher output and executes it."""
    if state.get("queue"):
        await state["queue"].put({"status": "executing", "message": "Executing Python code...", "node": "coder"})
        
    output = state.get("research_output", "")
    code_match = re.search(r"```python\n(.*?)\n```", output, re.DOTALL)
    
    if code_match:
        code = code_match.group(1)
        result = execute_python_code(code)
        state["execution_result"] = result
        if state.get("queue"):
            await state["queue"].put({"status": "executed", "message": f"Code Executed:\n{result}", "node": "coder"})
    else:
        state["execution_result"] = "Error: Could not extract valid python code block."
        
    return state

async def searcher_node(state: AgentState) -> AgentState:
    """Performs web search using Tavily search tool."""
    if state.get("queue"):
        await state["queue"].put({"status": "searching", "message": "Searching the web...", "node": "searcher"})
        
    output = state.get("research_output", "")
    query_match = re.search(r'ACTION:\s*WEB_SEARCH\s*\n\s*query\s*=\s*["\'](.*?)["\']', output, re.IGNORECASE | re.DOTALL)
    
    # Fallback regex if formatting differs slightly
    if not query_match:
        query_match = re.search(r'ACTION:\s*WEB_SEARCH\s*\n\s*query\s*=\s*(.*)', output, re.IGNORECASE)
        
    if query_match:
        from app.tools.search_tool import tavily_search
        query = query_match.group(1).strip()
        if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
            query = query[1:-1].strip()
            
        try:
            result = tavily_search._run(query)
            state["execution_result"] = result
            if state.get("queue"):
                await state["queue"].put({"status": "searched", "message": f"Search Completed: '{query}'", "node": "searcher"})
        except Exception as e:
            state["execution_result"] = f"Web Search Error: {str(e)}"
    else:
        state["execution_result"] = "Error: Could not extract valid web search query."
        
    return state

async def critic_node(state: AgentState) -> AgentState:
    if "Error:" in state.get("research_output", ""):
        return state

    if state.get("developer_resume_mode"):
        state["critique"] = "APPROVED"
        return state

    prompt = f"""
    You are a critical reviewer. Analyze the following research report:
    {state.get('research_output', '')}
    
    If the report is excellent, respond ONLY with "APPROVED".
    Otherwise, provide feedback.
    """
    
    response = await invoke_llm(prompt, None, state.get("llm_provider", "gemini"))
    state["critique"] = response
    return state

async def save_research_to_graph(state: AgentState) -> AgentState:
    research_content = state.get("research_output", "")
    query_topic = state.get("query", "General Research")
    
    if not research_content or "Error:" in research_content or "ACTION: CODE_EXECUTE" in research_content:
        state["storage_result"] = "Skipped: Research contained errors, was empty, or is still executing code."
        return state

    if not neo4j_manager.driver:
        state["storage_result"] = "Skipped: Neo4j database is unconfigured or offline."
        return state

    cypher_write_query = """
    MERGE (q:Concept {name: $topic})
    SET q.updatedAt = timestamp()
    
    MERGE (r:ResearchSummary {name: $topic + "_Summary"})
    SET r.raw_data = substring($content, 0, 2000),
        r.processedAt = timestamp()
        
    MERGE (q)-[:HAS_ANALYSIS]->(r)
    RETURN count(q) as created
    """
    
    try:
        await neo4j_manager.execute_query(cypher_write_query, parameters={
            "topic": query_topic,
            "content": research_content
        })
        storage_status = "Success: Saved parent node."
    except Exception as e:
        state["storage_result"] = f"Storage error: {str(e)}"
        return state

    # Dynamically extract and save rich concept relationships (Semantic Graph RAG)
    try:
        extraction_prompt = f"""
        Analyze the following research report and extract up to 5 core concept relationships.
        Output them strictly as a JSON array of objects with keys "source", "relationship", and "target".
        - "source" and "target" should be clean nouns/entities (max 3 words, e.g. "Neural Networks", "Llama 3").
        - "relationship" should be a single uppercase word with underscores (e.g. "BUILT_ON", "DEVELOPED_BY", "COMPETING_WITH").
        
        Example output:
        [
          {{"source": "Transformer", "relationship": "INVENTED_BY", "target": "Google"}},
          {{"source": "PyTorch", "relationship": "USED_FOR", "target": "Deep Learning"}}
        ]
        
        Report to analyze:
        {research_content[:3000]}
        
        Respond ONLY with the raw JSON array. Do not include markdown code block styling or any explanation.
        """
        
        extraction_response = await invoke_llm(extraction_prompt, None, state.get("llm_provider", "gemini"))
        
        cleaned_json = extraction_response.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[7:]
        elif cleaned_json.startswith("```"):
            cleaned_json = cleaned_json[3:]
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3]
        cleaned_json = cleaned_json.strip()
        
        relationships = json.loads(cleaned_json)
        
        saved_rels = []
        if isinstance(relationships, list):
            for rel in relationships:
                src = rel.get("source")
                relationship_type = rel.get("relationship")
                tgt = rel.get("target")
                if src and relationship_type and tgt:
                    await neo4j_manager.upsert_relationship(
                        source_node=src,
                        relationship=relationship_type,
                        target_node=tgt,
                        properties={"source_agent": "Astra_Extractor", "topic": query_topic}
                    )
                    saved_rels.append(f"({src})-[:{relationship_type}]->({tgt})")
            
            state["storage_result"] = f"Success: Saved concept summary & mapped {len(saved_rels)} semantic relationships: {', '.join(saved_rels)}"
        else:
            state["storage_result"] = "Success: Saved concept summary."
            
    except Exception as e:
        print(f"Graph RAG Semantic Extraction failed: {e}")
        state["storage_result"] = f"Success: Saved concept summary (relations extraction skipped: {str(e)})"
        
    return state

def should_continue_from_researcher(state: AgentState) -> str:
    output = state.get("research_output", "")
    if "ACTION: CODE_EXECUTE" in output:
        return "coder"
    if "ACTION: WEB_SEARCH" in output:
        return "searcher"
    return "critic"

def should_continue_from_critic(state: AgentState) -> str:
    critique = state.get('critique', '')
    rev_count = state.get('revision_count', 0)
    
    if "Error:" in state.get("research_output", "") or rev_count > 5:
        return "END"
    
    if "APPROVED" in critique.upper() or rev_count >= 2:
        return "storage"
    
    state["revision_count"] = rev_count + 1
    return "researcher"

workflow = StateGraph(AgentState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("searcher", searcher_node)
workflow.add_node("critic", critic_node)
workflow.add_node("storage", save_research_to_graph)

workflow.set_entry_point("researcher")
workflow.add_conditional_edges(
    "researcher",
    should_continue_from_researcher,
    {"coder": "coder", "searcher": "searcher", "critic": "critic"}
)
workflow.add_edge("coder", "researcher")
workflow.add_edge("searcher", "researcher")
workflow.add_conditional_edges(
    "critic", 
    should_continue_from_critic, 
    {"researcher": "researcher", "storage": "storage", "END": END}
)
workflow.add_edge("storage", END)
app_graph = workflow.compile()