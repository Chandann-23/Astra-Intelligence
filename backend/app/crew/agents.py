import os
import sys
import queue
import threading
import json
from typing import Generator
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool  # ✅ Use the decorator (most stable)
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Absolute import relative to /backend root
from app.tools.graph_tool import neo4j_manager

load_dotenv()

class CrewOutputCapture:
    def __init__(self):
        self.queue = queue.Queue()
        self._stop_event = threading.Event()

    def write(self, data):
        if data and data.strip():
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
        # Initialize LLM
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        # Initialize the search instance for use inside the tool
        self.tavily = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    @tool("tavily_search")
    def search_tool(self, query: str):
        """Search the internet for current facts, 2026 news, and technical data."""
        # We manually call the .run() method of the LangChain tool
        return self.tavily.run(query)

    @tool("neo4j_tool")
    def graph_tool(self, query: str):
        """Record technical concepts and relationships into the knowledge graph."""
        return neo4j_manager.upsert_graph_relationship(query)

    def researcher(self, history: str = "") -> Agent:
        backstory = "You are a 2026 Senior Research Analyst."
        if history:
            backstory += f"\n\nContext from previous conversation: {history}"
            
        return Agent(
            role="Senior Research Analyst",
            goal="Research {topic} and save findings to the knowledge graph using neo4j_tool.",
            backstory=backstory,
            llm=self.llm,
            # Pass the decorated methods directly
            tools=[self.search_tool, self.graph_tool],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    def critic(self, history: str = "") -> Agent:
        return Agent(
            role="Quality Lead",
            goal="Verify the accuracy of the research on {topic} and refine the final output.",
            backstory=f"You ensure logical soundness. Context: {history}",
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
                # Use class methods to get fresh agent instances
                researcher_agent = self.researcher(history)
                critic_agent = self.critic(history)
                
                t1 = Task(
                    description=f"Analyze the current state and future trajectory of {topic}.",
                    expected_output="A technical report with strategic recommendations.",
                    agent=researcher_agent
                )
                
                t2 = Task(
                    description=f"Review the research report on {topic}. Fix any logical errors.",
                    expected_output="A polished and verified final report.",
                    agent=critic_agent
                )
                
                astra_crew = Crew(
                    agents=[researcher_agent, critic_agent],
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