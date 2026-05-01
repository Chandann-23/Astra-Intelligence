import os
import json
from typing import TypedDict, Annotated, Generator
from dotenv import load_dotenv

# LangChain / LangGraph Imports
from langchain_huggingface import HuggingFaceEndpoint
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

# Phase 2: Initialize Hugging Face Inference API LLM
# Using Mistral Nemo for stable serverless API with high uptime
llm = HuggingFaceEndpoint(
    repo_id='mistralai/Mistral-Nemo-Instruct-2407',
    huggingfacehub_api_token=os.getenv('HUGGINGFACE_TOKEN'),
    task='text-generation',
    # Adding these parameters ensures the client communicates correctly
    content_type='application/json',
    temperature=0.7,
    max_new_tokens=1024
)

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
    
    response = llm.invoke(prompt)
    state["research_output"] = response.content
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
    
    response = llm.invoke(prompt)
    state["critique"] = response.content
    return state

# Phase 2: Create storage_node
def storage_node(state: AgentState) -> AgentState:
    """Save the final research to Neo4j"""
    try:
        from app.tools.graph_tool import neo4j_manager
        
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
        "storage": "storage"
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