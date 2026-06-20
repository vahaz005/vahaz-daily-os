import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def web_search(query: str, max_results: int = 4) -> str:
    """
    Searches the web using Tavily Client and returns a formatted string of results.
    """
    try:
        from tavily import TavilyClient
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY environment variable is not set."
        
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        results = response.get("results", [])
        
        formatted = []
        for r in results:
            title = r.get("title", "No Title")
            content = r.get("content", "")
            formatted.append(f"Title: {title}\nContent: {content[:400]}")
            
        if not formatted:
            return f"No search results found for: {query}"
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error during web search for '{query}': {str(e)}"

def fetch_arxiv(topic: str) -> str:
    """
    Fetches the top 3 papers from arXiv API for a given topic and returns a formatted string of results.
    """
    try:
        params = {
            "search_query": f"all:{topic}",
            "max_results": 3
        }
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(xml_data)
        
        formatted = []
        for entry in root.findall('atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            summary_elem = entry.find('atom:summary', ns)
            
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No Title"
            title = " ".join(title.split())
            
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No Summary"
            summary = " ".join(summary.split())
            
            formatted.append(f"Title: {title}\nSummary: {summary[:300]}")
            
        if not formatted:
            return f"No ArXiv papers found for topic: {topic}"
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error fetching from ArXiv for topic '{topic}': {str(e)}"
