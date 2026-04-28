import os
import sys
import queue
import threading
import json
from typing import Generator, Any, List
from crewai import Agent, Task, Crew, Process
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Ensure these imports match your actual file structure
from app.tools.graph_tool import neo4j_manager

load_dotenv()

class CrewOutputCapture:
    def __init__(self):
        self.queue = queue.Queue()
        self._stop_event = threading.Event()

    def write(self, data):
        if data and data.strip():
            # Clean ANSI escape codes if they appear in logs
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
        # Initialize the LLM
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        
        # Initialize the Search Tool
        # We define it here to ensure it's available for the researcher agent
        self.search_tool = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    def researcher(self, history: str = "") -> Agent:
        backstory = f"""You are a 2026 Senior Research Analyst. If the user asks for anything related 
            to 2025 or 2026, or if the information in the Knowledge Graph is outdated, 
            you MUST use the Tavily Search tool to find the most current facts.
            You ALWAYS use your 'neo4j_tool' to record every technical concept you find."""
        
        if history:
            backstory += f"\n\nPrevious conversation context:\n{history}"
            
        return Agent(
            role="Senior Research Analyst",
            goal="Research {topic} and save findings to the knowledge graph using neo4j_tool.",
            backstory=backstory,
            llm=self.llm,
            # We pass the neo4j_manager.tool (from your graph_tool.py) 
            # and the search_tool instance
            tools=[neo4j_manager.tool, self.search_tool],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    def critic(self, history: str = "") -> Agent:
        backstory = "You are a Quality Lead, expert at finding logical gaps and verifying data."
        if history:
            backstory += f"\n\nPrevious conversation context:\n{history}"

        return Agent(
            role="Quality Lead",
            goal="Verify the accuracy of the research on {topic}",
            backstory=backstory,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def research_task(self, topic: str, history: str = "") -> Task:
        return Task(
            description=f"Analyze the current state and future trajectory of {topic}. Record technical relationships in the graph.",
            expected_output="A detailed report with technical insights and strategic recommendations.",
            agent=self.researcher(history)
        )

    def review_task(self, topic: str, history: str = "") -> Task:
        return Task(
            description=f"Review the research report on {topic}. Check for factual errors and logical consistency.",
            expected_output="A polished, verified final report.",
            agent=self.critic(history)
        )

    def run_crew_stream(self, topic: str, history: str = "") -> Generator[str, None, None]:
        capture = CrewOutputCapture()
        old_stdout = sys.stdout
        sys.stdout = capture

        def run_kickoff():
            try:
                # Use local variables for agents/tasks within the thread
                research_agent = self.researcher(history)
                critic_agent = self.critic(history)
                
                t1 = self.research_task(topic, history)
                t2 = self.review_task(topic, history)
                
                astra_crew = Crew(
                    agents=[research_agent, critic_agent],
                    tasks=[t1, t2],
                    process=Process.sequential,
                    verbose=True
                )
                
                # Kickoff the crew process
                result = astra_crew.kickoff(inputs={"topic": topic, "history": history})
                
                # Format result correctly for the generator
                capture.write(f"__FINAL_RESULT__:{str(result)}")
            except Exception as e:
                capture.write(f"[ERROR]: {str(e)}")
            finally:
                capture.stop()
                sys.stdout = old_stdout

        thread = threading.Thread(target=run_kickoff)
        thread.start()

        yield from capture.get_logs()