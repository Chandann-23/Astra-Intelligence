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

class AstraCrew:
    def __init__(self):
        # Using string format bypasses Pydantic validation errors
        # CrewAI uses LiteLLM internally to handle this
        self.llm = "groq/llama-3.3-70b-versatile"
        self.tavily = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    @tool("tavily_search")
    def search_tool(self, query: str):
        """Search the internet for current 2026 data and facts."""
        return self.tavily.run(query)

    @tool("neo4j_tool")
    def graph_tool(self, query: str):
        """Save technical concepts and relationships to the knowledge graph."""
        return neo4j_manager.upsert_graph_relationship(query)

    def run_crew_stream(self, topic: str, history: str) -> Generator[str, None, None]:
        q = queue.Queue()
        
        def run_kickoff():
            try:
                # Minimalist Agent Setup
                researcher = Agent(
                    role="Senior Analyst",
                    goal=f"Research {topic} and save to graph.",
                    backstory="Expert 2026 researcher.",
                    llm=self.llm,
                    tools=[self.search_tool, self.graph_tool],
                    verbose=True
                )

                task = Task(
                    description=f"Analyze {topic} deeply.",
                    expected_output="Detailed technical report.",
                    agent=researcher
                )

                crew = Crew(
                    agents=[researcher],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=True
                )

                # Capture stdout logs to the queue
                class Logger:
                    def write(self, data):
                        if data.strip():
                            q.put(data.replace('\x1b', '').replace('[32m', '').replace('[0m', ''))
                    def flush(self): pass

                old_stdout = sys.stdout
                sys.stdout = Logger()
                
                result = crew.kickoff(inputs={"topic": topic})
                q.put(f"__FINAL_RESULT__:{str(result)}")
                
            except Exception as e:
                q.put(f"[ERROR]: {str(e)}")
            finally:
                sys.stdout = old_stdout
                q.put(None) # Signal end of stream

        threading.Thread(target=run_kickoff).start()

        while True:
            msg = q.get()
            if msg is None:
                break
            # Format for Server-Sent Events (SSE)
            yield f"data: {json.dumps({'type': 'log' if '__FINAL' not in msg else 'result', 'content': msg.replace('__FINAL_RESULT__:', '')})}\n\n"