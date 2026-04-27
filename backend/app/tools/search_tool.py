import os
from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

@tool("tavily_search")
def tavily_search(query: str):
    """
    Search the live web for 2026 data using Tavily. 
    Use this if information is missing from the graph or older than 2025.
    Returns the top 5 most relevant facts.
    """
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY not found in environment variables."
            
        client = TavilyClient(api_key=api_key)
        # Search for the query, get up to 5 results
        search_result = client.search(query=query, search_depth="advanced", max_results=5)
        
        if not search_result.get('results'):
            return "No relevant search results found on the live web."
            
        formatted_results = []
        for i, res in enumerate(search_result['results'], 1):
            title = res.get('title', 'No Title')
            content = res.get('content', 'No Content')
            url = res.get('url', 'No URL')
            formatted_results.append(f"{i}. {title}\n   Content: {content}\n   Source: {url}")
            
        return "Top 5 Live 2026 Search Results:\n\n" + "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Tavily Search Error: {str(e)}"
