import os
import sys
import queue
import threading
import json
from typing import Generator
from crewai import Agent, Task, Crew, Process
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from crewai.tools import Tool
from dotenv import load_dotenv

# Absolute import relative to /backend root
from app.tools.graph_tool import neo4j_manager

load_dotenv()

class CrewOutputCapture:
    """Captures stdout to stream agent 'thought' logs to the frontend."""
    def __init__(self):
        self.queue = queue.Queue()
        self._stop_event = threading.Event()

    def write(self, data):
        if data and data.strip():
            # Clean ANSI characters for a cleaner UI log
            clean_data = data.replace('\x1b', '').replace('[32m', '').replace('[0m', '')
            self.queue.put(clean_data)

    def flush(self):
        pass

    def get_logs(self) -> Generator[str, None, None]:
        while not self._stop_event.is_set() or not self.queue.empty():
            try:
                log = self.queue.get(timeout=0.1)
                yield log
            except queue.Empty:
                continue

    def stop(self):
        self._stop_event.set()

class AstraCrew:
    def __init__(self):
        # 1. Initialize LLM with standard Pydantic-friendly parameters
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        
        # 2. Wrap Tavily Search as a standard CrewAI Tool
        # This bypasses the validation errors by not passing the raw object
        tavily_instance = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))
        self.search_tool = Tool(
            name="tavily_search",
            description="Search the internet for current facts, 2026 news, and technical data.",
            func=tavily_instance.run
        )

        # 3. Explicitly wrap the Neo4j Manager function
        self.graph_tool = Tool(
            name="neo4j_tool",
            description="Record technical concepts and relationships into the knowledge graph.",
            func=neo4j_manager.upsert_graph_relationship 
        )

    def researcher(self, history: str = "") -> Agent:
        backstory = "You are a 2026 Senior Research Analyst. You specialize in deep-dive technical research."
        if history:
            backstory += f"\n\nContext from previous conversation: {history}"
            
        return Agent(
            role="Senior Research Analyst",
            goal="Research {topic} and save findings to the knowledge graph using neo4j_tool.",
            backstory=backstory,
            llm=self.llm,
            tools=[self.search_tool, self.graph_tool],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    def critic(self, history: str = "") -> Agent:
        backstory = "You are a Quality Lead. You ensure that the research report is logically sound and factually accurate."
        if history:
            backstory += f"\n\nContext from previous conversation: {history}"

        return Agent(
            role="Quality Lead",
            goal="Verify the accuracy of the research on {topic} and refine the final output.",
            backstory=backstory,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def run_crew_stream(self, topic: str, history: str = "") -> Generator[str, None, None]:
        capture = CrewOutputCapture()
        old_stdout = sys.stdout
        sys.stdout = capture

        def run_kickoff():
            try:
                # Initialize agents and tasks within the execution thread
                researcher = self.researcher(history)
                critic = self.critic(history)
                
                t1 = Task(
                    description=f"Analyze the current state and future trajectory of {topic}.",
                    expected_output="A technical report with strategic recommendations.",
                    agent=researcher
                )
                
                t2 = Task(
                    description=f"Review the research report on {topic}. Fix any logical errors.",
                    expected_output="A polished and verified final report.",
                    agent=critic
                )
                
                astra_crew = Crew(
                    agents=[researcher, critic],
                    tasks=[t1, t2],
                    process=Process.sequential,
                    verbose=True
                )
                
                result = astra_crew.kickoff(inputs={"topic": topic, "history": history})
                capture.write(f"__FINAL_RESULT__:{str(result)}")
                
            except Exception as e:
                capture.write(f"[ERROR]: {str(e)}")
            finally:
                capture.stop()
                sys.stdout = old_stdout

        thread = threading.Thread(target=run_kickoff)
        thread.start()

        yield from capture.get_logs()