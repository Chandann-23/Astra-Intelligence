import os
import sys
import queue
import threading
import json
from typing import Generator
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from app.tools.graph_tool import neo4j_manager

# LANGGRAPH MIGRATION - STABLE V1 API
# Migrated from CrewAI to LangGraph for better stability and control
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import os
import json

# Phase 2: Define AgentState with TypedDict fields
class AgentState(TypedDict):
    query: str
    research_output: str
    critique: str
    revision_count: int

# Phase 2: Initialize ChatGoogleGenerativeAI with explicit version='v1'
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    version="v1",  # Force stable v1 API
    google_api_key=os.getenv("GEMINI_API_KEY"),
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

# IF THE ABOVE STILL 404s, USE THIS 'NATIVE' FALLBACK:
# model="google/gemini-1.5-flash"

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
        # We only want basic results to keep the 'thought' clean
        search_result = client.search(query=query, search_type="web", max_results=3)
        
        # Extract ONLY the title and content snippets with context compression
        cleaned_results = []
        for r in search_result.get('results', []):
            content = r.get('content', '')[:400] # Limit each result to 400 chars to save tokens
            cleaned_results.append(f"Title: {r.get('title')}\nContent: {content}...")
        
        return "\n\n".join(cleaned_results)
    except Exception as e:
        return f"Tavily Search failed: {str(e)}"

@tool("neo4j_tool")
def graph_tool(query: str):
    """Execute a Cypher query against the Neo4j database to save research entities."""
    from app.tools.graph_tool import neo4j_manager
    
    try:
        # If your manager uses a generic query runner:
        result = neo4j_manager.execute_query(query) 
        return f"Successfully executed: {result}"
    except Exception as e:
        return f"Database Error: {str(e)}"

# The 'Scout' - High Rate Limits, very fast
# Use this for searching and parsing web data
researcher_llm = gemini_pro_llm

# The 'Commander' - Lower Rate Limits, very smart
# Use this only for final report synthesis
analyzer_llm = gemini_pro_llm

class AstraCrew:
    def __init__(self):
        # Dual LLM system for optimal token usage
        self.researcher_llm = researcher_llm
        self.analyzer_llm = analyzer_llm

    def run_crew_stream(self, topic: str, history: str) -> Generator[str, None, None]:
        q = queue.Queue()
        
        def run_kickoff():
            try:
                # 1. Researcher uses 8B model to save tokens
                researcher = Agent(
                    role='Lead Tech Researcher',
                    goal='Search the web and extract key technical entities',
                    backstory='Expert at high-volume data retrieval and entity extraction.',
                    llm=self.researcher_llm,
                    tools=[search_tool, graph_tool],
                    max_rpm=2,  # Slow down to prevent rate limit errors
                    max_iter=5,  # Circuit breaker: stop after 5 attempts
                    max_execution_time=120, # Increase to 2 minutes for complex tasks
                    verbose=True
                )

                # 2. Analyzer uses 70B model for final "Brain" work
                analyzer = Agent(
                    role='Chief Technical Analyst',
                    goal='Synthesize research data into a comprehensive report',
                    backstory='Master at finding patterns and deep reasoning.',
                    llm=self.analyzer_llm,
                    verbose=True
                )

                # 3. Memory uses Gemini Pro for deep analysis
                memory = Agent(
                    role='Knowledge Architect',
                    goal='Integrate research findings with existing knowledge graph data',
                    backstory='Expert at connecting new research with historical context using massive memory window.',
                    llm=gemini_pro_llm,
                    tools=[search_tool, graph_tool],
                    max_rpm=2,  # Slow down to prevent rate limit errors
                    max_iter=5,  # Circuit breaker: stop after 5 attempts
                    max_execution_time=120, # Increase to 2 minutes for complex tasks
                    verbose=True
                )

                # 3. Force Structure in Task
                t1 = Task(
                    description=f"Research {topic} and save entities to Neo4j.",
                    expected_output="Raw technical findings.",
                    agent=researcher
                )
                
                t2 = Task(
                    description="Review the findings. Add a hook introduction, 3 critical reasons why this matters, and a forward-looking conclusion.",
                    expected_output="A polished, strategic report with markdown headers.",
                    agent=analyzer
                )
                
                t3 = Task(
                    description="Integrate research findings with existing knowledge graph data using massive memory window.",
                    expected_output="Enhanced report with historical context and connections.",
                    agent=memory
                )
                
                crew = Crew(
                    agents=[researcher, analyzer, memory], 
                    tasks=[t1, t2, t3], 
                    process=Process.sequential, 
                    verbose=True
                )

                # Enhanced Logger to catch "Thought" for the Strategy Stream
                class Logger:
                    def write(self, data):
                        if data.strip():
                            # We send EVERYTHING to the queue; the yield logic handles routing
                            q.put(data)
                    def flush(self): pass

                sys.stdout = Logger()
                result = crew.kickoff(inputs={"topic": topic})
                q.put(f"__FINAL_RESULT__:{str(result)}")
                
            except Exception as e:
                q.put(f"[ERROR]: {str(e)}")
            finally:
                q.put(None)

        threading.Thread(target=run_kickoff).start()
        while True:
            msg = q.get()
            if msg is None: break
            
            # ROUTING LOGIC
            msg_type = 'log'
            # If the log looks like internal reasoning, send to Strategy Stream
            if any(x in msg for x in ["Thought:", "Action:", "Working Agent:"]):
                msg_type = 'strategy'
            elif "__FINAL_RESULT__" in msg:
                msg_type = 'result'

            yield f"data: {json.dumps({'type': msg_type, 'content': msg.replace('__FINAL_RESULT__:', '')})}\n\n"