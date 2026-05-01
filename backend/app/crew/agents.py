import os
import json
from typing import TypedDict, Annotated, Generator
from dotenv import load_dotenv

# LiteLLM AI Gateway Architecture
import litellm
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool

# Load environment variables FIRST
load_dotenv()

# GLM-5.1 Configuration via Hugging Face Gateway
# Ensure this matches the model name on HF or your provider's expected string
PRODUCTION_MODEL = "huggingface/zai-org/GLM-5.1"

# Phase 2: Define AgentState
class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int
    storage_result: str 

def invoke_llm(prompt: str) -> str:
    """Invoke LLM through LiteLLM AI Gateway with robust error handling"""
    
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    
    # Validation check to stop "False" key errors before they hit the API
    if not api_key:
        print("❌ CRITICAL ERROR: HUGGINGFACE_API_KEY is missing from environment!")
        return "Error: HUGGINGFACE_API_KEY not found. Please check Hugging Face Secrets."

    print(f"🚀 Astra Engine: Running on GLM-5.1 ({PRODUCTION_MODEL})")
    
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
        print(f"LiteLLM Error: {error_msg}")
        
        # Check specifically for authentication issues
        if "401" in error_msg or "auth" in error_msg.lower():
            return "Error: Authentication failed. Verify HUGGINGFACE_API_KEY."
            
        return f"Error: {error_msg}"

# --- Node Definitions ---

def researcher_node(state: AgentState) -> AgentState:
    """Analyze the query and generate a research report"""
    # Ensure revision_count is initialized
    if state.get("revision_count") is None:
        state["revision_count"] = 0
        
    prompt = f"""
    You are a research analyst. Analyze the following query:
    Query: {state.get('query', '')}
    Previous research: {state.get('research_output', '')}
    Previous critique: {state.get('critique', '')}
    Revision count: {state['revision_count']}
    
    Start directly with # Executive Summary or the first heading. Do not include any formal report headers, dates, or analyst role information.
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

def storage_node(state: AgentState) -> AgentState:
    """Save the final research to Neo4j"""
    # Skip storage if there was an error
    if "Error:" in state.get("research_output", ""):
        state["storage_result"] = "Skipped: Research contained errors."
        return state

    try:
        from app.tools.graph_tool import Neo4jManager
        neo4j_manager = Neo4jManager()
        
        cypher_query = """
        CREATE (r:Research {
            query: $query,
            content: $content,
            created: datetime()
        })
        RETURN r
        """
        params = {
            "query": state.get('query', ''),
            "content": state.get('research_output', '')
        }
        neo4j_manager.execute_query(cypher_query, params)
        state["storage_result"] = "Success: Saved to Neo4j"
    except Exception as e:
        state["storage_result"] = f"Storage error: {str(e)}"
    
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
workflow.add_node("storage", storage_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_conditional_edges(
    "critic", 
    should_continue, 
    {"researcher": "researcher", "storage": "storage", "END": END}
)
workflow.add_edge("storage", END)
app_graph = workflow.compile()