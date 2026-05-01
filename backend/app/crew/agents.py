import os
import json
from typing import TypedDict, Annotated, Generator
from dotenv import load_dotenv

# LiteLLM AI Gateway Architecture
import litellm
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

# Phase 2: Define AgentState
class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int
    storage_result: str  # Added to prevent key errors in storage_node

# Phase 2: Initialize LiteLLM AI Gateway
# Using astra-brain unified model with automatic fallback handling
def invoke_llm(prompt: str) -> str:
    """Invoke LLM through LiteLLM AI Gateway with fallback handling"""
    
    # HARDCODED PRODUCTION MODE - NO LOCALHOST DEPENDENCY
    print("🚀 Astra Engine: Running in DIRECT CLOUD mode (HARDCODED)")
    
    try:
        # Production ONLY - use Gemini directly through LiteLLM (let LiteLLM handle base_url)
        response = litellm.completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            api_key=os.getenv("GOOGLE_API_KEY")
            # CRITICAL: NO base_url for cloud direct access
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"LiteLLM Error: {str(e)}")
        
        # HARDCODED PRODUCTION FALLBACK - NO LOCALHOST
        try:
            # Production fallback - try Hugging Face
            response = litellm.completion(
                model="huggingface/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1024,
                api_key=os.getenv("HUGGINGFACE_TOKEN")
            )
            print("Production Fallback: Hugging Face model used")
            
            return response.choices[0].message.content
            
        except Exception as fallback_error:
            print(f"Fallback also failed: {str(fallback_error)}")
            return f"Error: Unable to process request - {str(e)}"

# Phase 2: Create researcher_node
def researcher_node(state: AgentState) -> AgentState:
    """Analyze the query and generate a research report"""
    prompt = f"""
    You are a research analyst. Analyze the following query and generate a comprehensive report:
    
    Query: {state.get('query', '')}
    Previous research: {state.get('research_output', '')}
    Previous critique: {state.get('critique', '')}
    Revision count: {state.get('revision_count', 0)}
    
    Provide a detailed analysis with insights, data points, and conclusions.
    """
    
    response = invoke_llm(prompt)
    
    # Check for error responses to prevent recursion limit
    if "Error:" in response or "error" in response.lower():
        print(f"Researcher node error detected: {response}")
        state["research_output"] = f"Research failed due to LLM error: {response}"
        state["revision_count"] = 5  # Force end condition
        return state
    
    state["research_output"] = response
    return state

# Phase 2: Create critic_node
def critic_node(state: AgentState) -> AgentState:
    """Review the report for depth and accuracy"""
    prompt = f"""
    You are a critical reviewer. Analyze the following research report:
    
    Research Output: {state.get('research_output', '')}
    
    Provide constructive feedback on:
    1. Accuracy and factual correctness
    2. Depth of analysis
    3. Completeness
    4. Areas for improvement
    
    If the report is excellent and needs no changes, respond with "APPROVED".
    Otherwise, provide specific feedback for revision.
    """
    
    response = invoke_llm(prompt)
    
    # Check for error responses to prevent recursion limit
    if "Error:" in response or "error" in response.lower():
        print(f"Critic node error detected: {response}")
        state["critique"] = f"Critique failed due to LLM error: {response}"
        state["revision_count"] = 5  # Force end condition
        return state
    
    state["critique"] = response
    return state

# Phase 2: Create storage_node
def storage_node(state: AgentState) -> AgentState:
    """Save the final research to Neo4j"""
    try:
        from app.tools.graph_tool import Neo4jManager
        
        # Create a new Neo4jManager instance
        neo4j_manager = Neo4jManager()
        
        # Create a simple node with the research output
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
        
        result = neo4j_manager.execute_query(cypher_query, params)
        state["storage_result"] = f"Research saved to Neo4j"
        
    except Exception as e:
        state["storage_result"] = f"Storage error: {str(e)}"
    
    return state

# Phase 2: Workflow Logic
def should_continue(state: AgentState) -> str:
    """Determine if we should continue revising or move to storage"""
    critique = state.get('critique', '')
    revision_count = state.get('revision_count', 0)
    research_output = state.get('research_output', '')
    
    # Check for errors to prevent infinite loops - skip all nodes on research error
    if "Error:" in research_output or "error" in research_output.lower():
        print("Error detected in research output, forcing end of workflow")
        return "END"
    
    # If critique says approved or we've revised twice, move to storage
    if "APPROVED" in critique.upper() or revision_count >= 2:
        return "storage"
    else:
        # Increment revision count
        state["revision_count"] = revision_count + 1
        return "researcher"

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("researcher", researcher_node)
workflow.add_node("critic", critic_node)
workflow.add_node("storage", storage_node)

# Add edges
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_conditional_edges(
    "critic", 
    should_continue, 
    {
        "researcher": "researcher",
        "storage": "storage",
        "END": END
    }
)
workflow.add_edge("storage", END)

# Final Compiled Graph
app_graph = workflow.compile()

# Tool definitions (kept for your integration needs)
@tool("tavily_search")
def search_tool(query: str):
    """Search web for real-time information."""
    from tavily import TavilyClient
    t_api_key = os.environ.get("TAVILY_API_KEY")
    if not t_api_key:
        return "Error: Missing Tavily API Key."
    try:
        client = TavilyClient(api_key=t_api_key)
        result = client.search(query, max_results=5)
        return f"Search results: {result}"
    except Exception as e:
        return f"Search error: {str(e)}"

@tool("graph_tool")
def graph_tool_executor(query: str):
    """Execute a Cypher query against the Neo4j database."""
    from app.tools.graph_tool import neo4j_manager
    try:
        result = neo4j_manager.execute_query(query) 
        return f"Success: {result}"
    except Exception as e:
        return f"Database Error: {str(e)}"