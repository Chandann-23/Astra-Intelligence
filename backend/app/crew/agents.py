import os
import json
import time
from typing import TypedDict, Annotated, Generator
from dotenv import load_dotenv

# LiteLLM AI Gateway Architecture
import litellm
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool

# Load environment variables FIRST
load_dotenv()

# High-Performance Llama Configuration via SambaNova Free Tier
# Use top-tier Meta-Llama-3.3-70B-Instruct for maximum speed and capability
PRODUCTION_MODEL = "sambanova/Meta-Llama-3.3-70B-Instruct"

# Phase 2: Define AgentState
class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int
    storage_result: str 

def invoke_llm(prompt: str) -> str:
    """Invoke LLM through LiteLLM AI Gateway with robust error handling and retries"""
    
    api_key = os.getenv("SAMBANOVA_API_KEY")
    
    # Validation check to stop "False" key errors before they hit the API
    if not api_key:
        print("❌ CRITICAL ERROR: SAMBANOVA_API_KEY is missing from environment!")
        return "Error: SAMBANOVA_API_KEY not found. Please check SambaNova Secrets."

    print(f"🚀 Astra Engine: Running on GLM-5.1 ({PRODUCTION_MODEL})")
    
    # Retry logic for rate limit errors
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # LiteLLM call optimized for GLM-5.1's long-horizon capabilities
            response = litellm.completion(
                model=PRODUCTION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096, # Increased to prevent mid-sentence cutoffs
                api_key=api_key,
                timeout=300 # Supports GLM-5.1's 8-hour research sessions
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"LiteLLM Error (attempt {attempt + 1}): {error_msg}")
            
            # Check specifically for rate limit errors
            if "rate limit" in error_msg.lower() or "ratelimit" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"⏳ Rate limit hit. Waiting 10 seconds before retry...")
                    time.sleep(10)
                    continue
                else:
                    return "Error: Rate limit exceeded. Please try again in a few minutes."
            
            # Check specifically for authentication issues
            if "401" in error_msg or "auth" in error_msg.lower():
                return "Error: Authentication failed. Verify HUGGINGFACE_API_KEY."
                
            # For other errors, don't retry
            if attempt == 0:  # Only return non-rate-limit errors immediately
                return f"Error: {error_msg}"
    
    return "Error: Failed after multiple attempts."

# --- Node Definitions ---

def researcher_node(state: AgentState) -> AgentState:
    """Analyze the query and generate a research report"""
    # Rate limit protection - add delay
    time.sleep(3)
    
    # Ensure revision_count is initialized and increment it
    if state.get("revision_count") is None:
        state["revision_count"] = 0
    else:
        state["revision_count"] += 1
        
    prompt = f"""
    You are a research analyst. Analyze the following query:
    Query: {state.get('query', '')}
    Previous research: {state.get('research_output', '')}
    Previous critique: {state.get('critique', '')}
    Revision count: {state['revision_count']}
    
    Provide a detailed analysis with insights, data points, and conclusions.
    """
    
    response = invoke_llm(prompt)
    
    if "Error:" in response:
        state["research_output"] = response
        # Terminate early on API failure
        state["revision_count"] = 99 
    else:
        state["research_output"] = response
        
    return state

def critic_node(state: AgentState) -> AgentState:
    """Review the report for depth and accuracy"""
    # Rate limit protection - add delay
    time.sleep(3)
    
    # Don't run critique if research failed
    if "Error:" in state.get("research_output", ""):
        return state

    prompt = f"""
    You are a critical reviewer. Analyze the following research report:
    {state.get('research_output', '')}
    
    If the report is excellent, respond ONLY with "APPROVED".
    Otherwise, provide feedback.
    """
    
    response = invoke_llm(prompt)
    state["critique"] = response
    return state

from langchain_community.graphs import Neo4jGraph

# Grab the active instance connection wrapper
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD")
)

def save_research_to_graph(state: AgentState) -> AgentState:
    """LangGraph node to force-commit research entities to Neo4j Cloud Instance"""
    research_content = state.get("research_output", "")
    query_topic = state.get("query", "General Research")
    
    if not research_content or "Error:" in research_content:
        print("[SYSTEM_WARN]: No valid content available to write to Neo4j.")
        state["storage_result"] = "Skipped: Research contained errors or was empty."
        return state

    # Constructing an explicit Cypher execution statement to guarantee node creation
    cypher_write_query = """
    MERGE (q:Concept {id: $topic})
    SET q.updatedAt = timestamp()
    
    // Split content briefly into summary elements to simulate structured extraction nodes
    MERGE (r:ResearchSummary {id: $topic + "_Summary"})
    SET r.raw_data = substring($content, 0, 2000),
        r.processedAt = timestamp()
        
    MERGE (q)-[:HAS_ANALYSIS]->(r)
    RETURN count(q) as created
    """
    
    try:
        # Execute transactional query directly on Aura instance
        result = graph.query(cypher_write_query, params={
            "topic": query_topic,
            "content": research_content
        })
        print(f"[SUCCESS]: Forced write to Neo4j Aura. Core transaction committed: {result}")
        state["storage_result"] = "Success: Forced write to Neo4j Aura"
    except Exception as db_err:
        print(f"[CRITICAL_ERROR]: Failed writing graph document to Neo4j Instance: {str(db_err)}")
        state["storage_result"] = f"Storage error: {str(db_err)}"
        
    return state

# --- Workflow Logic ---

def should_continue(state: AgentState) -> str:
    critique = state.get('critique', '')
    rev_count = state.get('revision_count', 0)
    
    # Immediate exit on errors
    if "Error:" in state.get("research_output", "") or rev_count > 5:
        return "END"
    
    if "APPROVED" in critique.upper() or rev_count >= 2:
        return "storage"
    
    # Update revision count in state before looping back
    state["revision_count"] = rev_count + 1
    return "researcher"

# Build Graph
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