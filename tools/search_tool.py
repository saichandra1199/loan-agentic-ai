import os
import requests
from crewai.tools import tool

@tool("Web Search Tool")
def web_search(query: str) -> str:
    """
    Search the web using Serper API for loan processing rules,
    RBI guidelines, CIBIL thresholds, FOIR limits, etc.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "SERPER_API_KEY not set. Web search unavailable."

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": 5}

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=10
        )
        data = response.json()
        results = []
        for item in data.get("organic", []):
            results.append(f"- **{item.get('title')}**: {item.get('snippet')} ({item.get('link')})")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"