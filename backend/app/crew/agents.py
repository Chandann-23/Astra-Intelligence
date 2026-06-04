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
                fallback_msg = f"\n\n⚠️ *[Astra Engine: Primary provider ({provider.upper()}) rate-limited or quota exceeded. Switching to {current_provider.upper()} to complete research...]*\n\n"
                accumulated_text += fallback_msg
                if queue:
                    await queue.put({"partial_result": fallback_msg})
                    await queue.put({
                        "status": "processing",
                        "message": f"Switching to fallback: {current_provider.upper()}...",
                        "node": "researcher"
                    })
                    
            result = await _invoke_llm_with_retry(messages, queue, current_provider)
            
            if isinstance(result, str) and result.startswith("Error:"):
                raise Exception(result)
                
            return accumulated_text + result
            
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
    
    if rag_mode == "strict_local":
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
        You are an advanced AI research analyst with code execution capabilities.
        If you need to perform calculations, data processing, or run python code to answer the query, output EXACTLY the following format:
        ACTION: CODE_EXECUTE
        ```python
        <your python code here>
        ```
        If you do not need to run code, or if you already have the execution result you need, provide a detailed analysis with insights, data points, and conclusions.
        
        Code Execution Result: {execution_result}
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

async def critic_node(state: AgentState) -> AgentState:
    if "Error:" in state.get("research_output", ""):
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
        state["storage_result"] = "Success: Wrote to Neo4j Async"
    except Exception as e:
        state["storage_result"] = f"Storage error: {str(e)}"
        
    return state

def should_continue_from_researcher(state: AgentState) -> str:
    output = state.get("research_output", "")
    if "ACTION: CODE_EXECUTE" in output:
        return "coder"
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
workflow.add_node("critic", critic_node)
workflow.add_node("storage", save_research_to_graph)

workflow.set_entry_point("researcher")
workflow.add_conditional_edges(
    "researcher",
    should_continue_from_researcher,
    {"coder": "coder", "critic": "critic"}
)
workflow.add_edge("coder", "researcher")
workflow.add_conditional_edges(
    "critic", 
    should_continue_from_critic, 
    {"researcher": "researcher", "storage": "storage", "END": END}
)
workflow.add_edge("storage", END)
app_graph = workflow.compile()