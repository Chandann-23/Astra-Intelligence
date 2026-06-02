import os
import json
import asyncio
from typing import TypedDict, Annotated, Any
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from litellm.exceptions import RateLimitError

import litellm
from langgraph.graph import StateGraph, END
from app.tools.graph_tool import neo4j_manager

load_dotenv()

class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int
    storage_result: str
    queue: Any # asyncio.Queue
    rag_mode: str

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def _invoke_llm_with_retry(prompt: str, queue: asyncio.Queue = None) -> str:
    """Invoke LLM through LiteLLM with async streaming and tenacity backoff"""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        return "Error: API key not found in environment."

    model = "gemini/gemini-2.0-flash" if os.getenv("GOOGLE_API_KEY") else "sambanova/Meta-Llama-3.3-70B-Instruct"

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
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

async def invoke_llm(prompt: str, queue: asyncio.Queue = None) -> str:
    try:
        return await _invoke_llm_with_retry(prompt, queue)
    except RetryError:
        return "Error: System is experiencing high traffic on the free tier API (Rate Limit Exceeded). Please wait a few seconds and try again."
    except Exception as e:
        return f"Error: {str(e)}"

async def researcher_node(state: AgentState) -> AgentState:
    if state.get("revision_count") is None:
        state["revision_count"] = 0
    else:
        state["revision_count"] += 1
        
    rag_mode = state.get("rag_mode", "general")
    
    if rag_mode == "strict_local":
        docs, reasoning = await neo4j_manager.document_vector_search(state.get('query', ''))
        context = "\n".join(docs)
        
        prompt = f"""
        You are a STRICT Local RAG assistant (NotebookLM mode). You must answer the user's query ONLY using the provided Context Notes below.
        DO NOT use any outside internet knowledge. If the answer is not contained in the Context Notes, say exactly: "I cannot find the answer in the provided notes."
        
        Context Notes:
        {context}
        
        Query: {state.get('query', '')}
        Previous research: {state.get('research_output', '')}
        Previous critique: {state.get('critique', '')}
        """
        if state.get("queue"):
            await state["queue"].put({"status": "researching", "message": f"Scanning local documents: {reasoning}", "node": "researcher"})
    else:
        prompt = f"""
        You are a research analyst. Analyze the following query:
        Query: {state.get('query', '')}
        Previous research: {state.get('research_output', '')}
        Previous critique: {state.get('critique', '')}
        Revision count: {state['revision_count']}
        
        Provide a detailed analysis with insights, data points, and conclusions.
        """
    
    response = await invoke_llm(prompt, state.get("queue"))
    
    if "Error:" in response:
        state["research_output"] = response
        state["revision_count"] = 99 
    else:
        state["research_output"] = response
        
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
    
    response = await invoke_llm(prompt, state.get("queue"))
    state["critique"] = response
    return state

async def save_research_to_graph(state: AgentState) -> AgentState:
    research_content = state.get("research_output", "")
    query_topic = state.get("query", "General Research")
    
    if not research_content or "Error:" in research_content:
        state["storage_result"] = "Skipped: Research contained errors or was empty."
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

def should_continue(state: AgentState) -> str:
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
workflow.add_node("critic", critic_node)
workflow.add_node("storage", save_research_to_graph)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_conditional_edges(
    "critic", 
    should_continue, 
    {"researcher": "researcher", "storage": "storage", "END": END}
)
workflow.add_edge("storage", END)
app_graph = workflow.compile()