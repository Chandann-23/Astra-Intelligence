import os
import sys
import queue
import threading
import json
from typing import Generator
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from app.tools.graph_tool import neo4j_manager

@tool("tavily_search")
def search_tool(query: str):
    """Search the internet for technical data or current events."""
    try:
        # We initialize the search inside the tool to avoid 'self' issues
        search = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))
        results = search.run(query.replace("'", ""))
        # Return a simplified version so the LLM doesn't choke on huge metadata
        return str(results)[:2000]
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool("neo4j_tool")
def graph_tool(query: str):
    """Save technical entities and relationships to the knowledge graph."""
    # Use the global neo4j_manager import - Fixed self parameter issue
    return neo4j_manager.upsert_graph_relationship(query)

class AstraCrew:
    def __init__(self):
        # String format requires the 'litellm' package we added to requirements
        self.llm = "groq/llama-3.3-70b-versatile"

    def run_crew_stream(self, topic: str, history: str) -> Generator[str, None, None]:
        q = queue.Queue()
        
        def run_kickoff():
            try:
                # 1. Bring back the Researcher
                researcher = Agent(
                    role="Lead Tech Researcher",
                    goal=f"Perform deep-dive research on {topic}",
                    backstory="Expert at finding obscure technical details.",
                    llm=self.llm,
                    tools=[search_tool, graph_tool],
                    verbose=True
                )

                # 2. Bring back the Critic (The "Blandness" Killer)
                critic = Agent(
                    role="Chief Strategy Officer",
                    goal="Transform raw research into a structured, executive report.",
                    backstory="You specialize in introductions, critical analysis, and conclusions.",
                    llm=self.llm,
                    verbose=True
                )

                # 3. Force the Structure in the Task
                t1 = Task(
                    description=f"Research {topic} and save entities to Neo4j.",
                    expected_output="Raw technical findings.",
                    agent=researcher
                )

                t2 = Task(
                    description="Review the findings. Add a hook introduction, 3 critical reasons why this matters, and a forward-looking conclusion.",
                    expected_output="A polished, strategic report with markdown headers.",
                    agent=critic
                )

                crew = Crew(agents=[researcher, critic], tasks=[t1, t2], verbose=True)

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