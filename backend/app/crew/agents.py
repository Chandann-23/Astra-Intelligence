import os
import sys
import queue
import threading
from typing import Generator, Any
from crewai import Agent, Task, Crew, Process
# ✅ Use the LangChain version of Tavily (Standard for 2026)
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from ..tools.graph_tool import upsert_graph_relationship, retrieve_knowledge

load_dotenv()

class CrewOutputCapture:
    def __init__(self):
        self.queue = queue.Queue()
        self._stop_event = threading.Event()

    def write(self, data):
        if data and data.strip():
            self.queue.put(data)

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
        self.llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        # ✅ Initialize the tool here
        self.search_tool = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    def researcher(self, history: str = "") -> Agent:
        backstory = f"""You are a 2026 researcher. If the user asks for anything related 
            to 2025 or 2026, or if the information in the Knowledge Graph is outdated, 
            you MUST use the Tavily Search tool to find the most current facts.
            You ALWAYS use your 'graph_tool' to record every technical concept you find."""
        if history:
            backstory += f"\n\nPrevious conversation context:\n{history}"
            
        
        # ... (Rest of your agent code is fine) ...
        return Agent(
            role="Senior Research Analyst",
            goal="Research {topic} AND save findings to the knowledge graph.",
            backstory="...",
            llm=self.llm,
            tools=[upsert_graph_relationship, retrieve_knowledge, self.search_tool],
            verbose=True,
            allow_delegation=False
        )

    def critic(self, history: str = "") -> Agent:
        backstory = "Expert at finding logical gaps."
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
        description = f"Analyze the current state and future trajectory of {topic}."
        if history:
            description += f" Consider the previous conversation context provided in your backstory."
            
        return Task(
            description=description,
            expected_output="A detailed, multi-section report with technical insights and strategic recommendations.",
            agent=self.researcher(history)
        )

    def review_task(self, topic: str, history: str = "") -> Task:
        description = f"Review the research report on {topic}. Check for factual errors and ensure all logical connections are sound."
        if history:
            description += f" Ensure the review aligns with the previous conversation context."

        return Task(
            description=description,
            expected_output="A polished, verified, and enhanced final report that corrected any initial errors.",
            agent=self.critic(history)
        )

    def run_crew_stream(self, topic: str, history: str = "") -> Generator[str, None, None]:
        capture = CrewOutputCapture()
        old_stdout = sys.stdout
        sys.stdout = capture

        def run_kickoff():
            try:
                # Re-initializing agents inside the thread to ensure fresh LLM state
                agents = [self.researcher(history), self.critic(history)]
                tasks = [self.research_task(topic, history), self.review_task(topic, history)]
                
                astra_crew = Crew(
                    agents=agents,
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True
                )
                
                result = astra_crew.kickoff(inputs={"topic": topic, "history": history})
                capture.write(f"__FINAL_RESULT__:{result}")
            except Exception as e:
                capture.write(f"[ERROR]: {str(e)}")
            finally:
                capture.stop()
                sys.stdout = old_stdout

        thread = threading.Thread(target=run_kickoff)
        thread.start()

        yield from capture.get_logs()