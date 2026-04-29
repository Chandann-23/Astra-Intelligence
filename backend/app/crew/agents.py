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
        """Search internet for technical data or current events."""
        # Clean query of problematic characters
        clean_query = query.replace("'", "").replace('"', "")
        return self.tavily.run(clean_query)

    @tool("neo4j_tool")
    def graph_tool(self, query: str):
        """Save technical concepts to the graph."""
        return neo4j_manager.upsert_graph_relationship(query)

    def run_crew_stream(self, topic, history):
        q = queue.Queue()
        def run_kickoff():
            try:
                res = Agent(role="Analyst", goal="Research {topic}", backstory="Expert", llm=self.llm, tools=[self.search_tool, self.graph_tool])
                task = Task(
                description=(
                    f"1. Research {topic} deeply.\n"
                    f"2. MANDATORY: Use the neo4j_tool to save at least 3 key technical entities "
                    f"and their relationships to the knowledge graph."
                ),
                expected_output="A report and a confirmation that data was saved to Neo4j.",
                agent=res
            )
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
            
            # Logic to route messages to Strategy Stream
            msg_type = 'log'
            # If message contains agent thinking patterns, send to Strategy
            if any(key in msg for key in ["Thought:", "Action:", "Action Input:", "Observation:"]):
                msg_type = 'strategy'
            elif "__FINAL_RESULT__" in msg:
                msg_type = 'result'

            yield f"data: {json.dumps({'type': msg_type, 'content': msg.replace('__FINAL_RESULT__:', '')})}\n\n"