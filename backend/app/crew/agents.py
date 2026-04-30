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

# The 'Memory' - Massive context window for complex research
# Use this for deep analysis and synthesis
gemini_pro_llm = LLM(
    model="gemini/gemini-1.5-flash", 
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7
)

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