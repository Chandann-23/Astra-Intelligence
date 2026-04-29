import os
import sys
import queue
import threading
import json
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from app.tools.graph_tool import neo4j_manager

class AstraCrew:
    def __init__(self):
        # String format requires the 'litellm' package we added to requirements
        self.llm = "groq/llama-3.3-70b-versatile"
        self.tavily = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    @tool("tavily_search")
    def search_tool(self, query: str):
        """Search internet for 2026 facts."""
        return self.tavily.run(query)

    @tool("neo4j_tool")
    def graph_tool(self, query: str):
        """Save technical concepts to the graph."""
        return neo4j_manager.upsert_graph_relationship(query)

    def run_crew_stream(self, topic, history):
        q = queue.Queue()
        def run_kickoff():
            try:
                res = Agent(role="Analyst", goal="Research {topic}", backstory="Expert", llm=self.llm, tools=[self.search_tool, self.graph_tool])
                task = Task(description=f"Analyze {topic}", expected_output="Report", agent=res)
                crew = Crew(agents=[res], tasks=[task], verbose=True)
                
                # Redirect stdout to capture agent thoughts
                class Logger:
                    def write(self, data):
                        if data.strip(): q.put(data.replace('\x1b', '').replace('[32m', '').replace('[0m', ''))
                    def flush(self): pass

                old_stdout = sys.stdout
                sys.stdout = Logger()
                result = crew.kickoff(inputs={"topic": topic})
                q.put(f"__FINAL_RESULT__:{result}")
            except Exception as e:
                q.put(f"[ERROR]: {str(e)}")
            finally:
                sys.stdout = old_stdout
                q.put(None)

        threading.Thread(target=run_kickoff).start()
        while True:
            msg = q.get()
            if msg is None: break
            yield f"data: {json.dumps({'type': 'log' if '__FINAL' not in msg else 'result', 'content': msg.replace('__FINAL_RESULT__:', '')})}\n\n"