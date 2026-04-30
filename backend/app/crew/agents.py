import os

from typing import Generator
from langchain_community.tools.tavily_search import TavilySearchResults
from app.tools.graph_tool import neo4j_manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LANGGRAPH MIGRATION - STABLE V1 API
# Migrated from CrewAI to LangGraph for better stability and control
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from typing import TypedDict, Annotated
import json

# Phase 2: Define AgentState with TypedDict fields
class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int

# Phase 2: Initialize ChatGoogleGenerativeAI with explicit version='v1'
api_key = os.getenv('GOOGLE_API_KEY')
print('API Key loaded:', bool(api_key))

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    model_kwargs={"version": "v1"},  # Force stable v1 API
    google_api_key=api_key,
    temperature=0.7
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
        query = """
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
        
        result = neo4j_manager.execute_query(query, params)
        state["storage_result"] = f"Research saved to Neo4j: {result}"
        
    except Exception as e:
        state["storage_result"] = f"Storage error: {str(e)}"
    
    return state

# Phase 2: Compile app_graph with flow logic
def should_continue(state: AgentState) -> str:
    """Determine if we should continue revising or move to storage"""
    critique = state.get('critique', '')
    revision_count = state.get('revision_count', 0)
    
    # If critique says approved or we've revised twice, move to storage
    if "APPROVED" in critique or revision_count >= 2:
        return "storage"
    else:
        # Increment revision count and go back to researcher
        state["revision_count"] = revision_count + 1
        return "researcher"

# Create the graph
app_graph = StateGraph(AgentState)

# Add nodes
app_graph.add_node("researcher", researcher_node)
app_graph.add_node("critic", critic_node)
app_graph.add_node("storage", storage_node)

# Add edges
app_graph.set_entry_point("researcher")
app_graph.add_edge("researcher", "critic")
app_graph.add_conditional_edges("critic", should_continue, {
    "researcher": "researcher",
    "storage": "storage"
})
app_graph.add_edge("storage", END)

# Compile the graph
app_graph = app_graph.compile()

# Tool definitions for LangGraph
@tool("tavily_search")
def search_tool(query: str):
    """Search web for real-time information."""
    import os
    from tavily import TavilyClient

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: Missing Tavily API Key."

    try:
        client = TavilyClient(api_key=api_key)
        result = client.search(query, max_results=5)
        return f"Search results for '{query}': {result}"
    except Exception as e:
        return f"Search error: {str(e)}"

@tool("graph_tool")
def graph_tool(query: str):
    """Execute a Cypher query against the Neo4j database to save research entities."""
    from app.tools.graph_tool import neo4j_manager
    
    try:
        # If your manager uses a generic query runner:
        result = neo4j_manager.execute_query(query) 
        return f"Successfully executed: {result}"
    except Exception as e:
        return f"Database Error: {str(e)}"