import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiolimiter import AsyncLimiter
from langchain_core.tools import tool
from datetime import datetime
import coloredlogs

# Import necessary functionality from RULAC_tools
try:
    from tools.RULAC_tools import Citation, RULAC_TOOL_RESULT, create_standard_citation, format_standard_tool_result
except ImportError:
    # Define types here if imports fail
    class Citation(TypedDict):
        """TypedDict for standardized citation format"""
        title: str
        url: str
        formatted_content: str
    
    class RULAC_TOOL_RESULT(TypedDict):
        """TypedDict for standardized tool result format"""
        content: Union[str, List[Dict[str, Any]], Dict[str, Any]]
        citations: List[Citation]
        tool_use_metadata: Optional[Dict[str, Any]]
    
    def create_standard_citation(title: str, url: str, formatted_content: str = "") -> Citation:
        """Create a standard citation dictionary"""
        return {"title": title, "url": url, "formatted_content": formatted_content}
    
    def format_standard_tool_result(content, citations, tool_name=None, tool_params=None, beacon_tool_source="BRAVE"):
        """Format tool results in a standardized structure"""
        tool_use_metadata = None
        if tool_name or tool_params:
            tool_use_metadata = {
                "tool_source": beacon_tool_source,
                "tool_name": tool_name,
                "tool_params": tool_params or {}
            }
        
        return {
            "content": content,
            "citations": citations,
            "tool_use_metadata": tool_use_metadata
        }

# Configure logging
logger = logging.getLogger("BRAVE_tools")
coloredlogs.install(
    logger=logger,
    level="INFO",
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
)
# Make logger accessible as log throughout the code
log = logger

# API Configuration
API_MAX_CONCURRENT_REQUESTS = 1
API_RPS = 1
API_RATE_LIMIT = AsyncLimiter(API_RPS, 1)
API_TIMEOUT = 20

# Brave Search API Key
API_KEY = "BSAsCIPqaPLhXXcAs1ysPXNIWhVP0gw"

# Brave Search API host
API_HOST = "https://api.search.brave.com"

# Brave Search API subpaths
API_PATH = {
    "web": urljoin(API_HOST, "res/v1/web/search"),
    "summarizer_search": urljoin(API_HOST, "res/v1/summarizer/search"),
}

# Create request headers for specific endpoints
API_HEADERS = {
    "web": {"X-Subscription-Token": API_KEY, "Api-Version": "2023-10-11"},
    "summarizer": {"X-Subscription-Token": API_KEY, "Api-Version": "2024-04-23"},
}

class BraveSearchSummary(BaseModel):
    """Model for Brave search summary results"""
    title: str = Field(..., description="The title of the search result")
    content: str = Field(..., description="The summarized content or answer")
    query: str = Field(..., description="The original search query")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Sources used to generate the summary")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="Images related to the search query")


async def brave_search_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Execute a search query using Brave Search API and return the summarized results.
    
    Args:
        query: The search query string
        
    Returns:
        Optional dictionary containing search results and summary
    """
    # Create web search request params
    api_params_web = {
        "q": query,
        "summary": 1,
    }
    
    try:
        async with API_RATE_LIMIT:
            async with ClientSession(
                connector=TCPConnector(limit=API_MAX_CONCURRENT_REQUESTS),
                timeout=ClientTimeout(API_TIMEOUT),
            ) as session:
                # Fetch web search results to get a summary key
                async with session.get(
                    API_PATH["web"],
                    params=api_params_web,
                    headers=API_HEADERS["web"],
                ) as response:
                    log.debug(f"Querying url: [{response.url}]")
                    data = await response.json()
                    status = response.status

                if status != 200:
                    log.error(
                        f"Failure getting web search results: {json.dumps(data, indent=2)}"
                    )
                    return None

                # Get the summary key from web search results
                summary_key = data.get("summarizer", {}).get("key")

                if not summary_key:
                    log.error("Failure getting summary key")
                    return None

                log.debug(f"Summarizer Key: [{summary_key}]")

                # Fetch summary with the key
                async with session.get(
                    url=API_PATH["summarizer_search"],
                    params={"key": summary_key, "entity_debug": 1},
                    headers=API_HEADERS["summarizer"],
                ) as response:
                    log.debug(f"Querying url: [{response.url}]")
                    summary_data = await response.json()
                    status = response.status

                    if status != 200:
                        log.error(
                            f"Failure getting summary: {json.dumps(summary_data, indent=2)}"
                        )
                        return None
                    
                    return summary_data
    except Exception as e:
        log.error(f"Error during Brave search query: {str(e)}")
        return None


def process_brave_summary(data: Dict[str, Any], query: str) -> BraveSearchSummary:
    """
    Process raw Brave search API response into a structured format.
    
    Args:
        data: Raw response data from Brave API
        query: Original search query
        
    Returns:
        BraveSearchSummary object with processed data
    """

    log.debug(f"Processing Brave search summary for query: {query}")
    log.debug(f"Raw data: {json.dumps(data, indent=2)}")

    
    # Extract title
    title = data.get("title", "Search Results")
    
    # Extract content from summary
    content = ""
    if "summary" in data:
        # Extract text from summary tokens
        for item in data["summary"]:
            if item.get("type") == "token" and "data" in item:
                content += item["data"]
    
    # If enrichments.raw exists, prefer that as it's the complete text
    if "enrichments" in data and "raw" in data["enrichments"]:
        content = data["enrichments"]["raw"]
    
    # Extract sources/context
    sources = []
    if "enrichments" in data and "context" in data["enrichments"]:
        for ctx in data["enrichments"]["context"]:
            sources.append({
                "title": ctx.get("title", "Unknown Source"),
                "url": ctx.get("url", "")
            })
    
    # Extract images
    images = []
    if "enrichments" in data and "images" in data["enrichments"]:
        for img in data["enrichments"]["images"]:
            image_data = {
                "url": img.get("url", ""),
                "text": img.get("text", "")
            }
            if "thumbnail" in img and "src" in img["thumbnail"]:
                image_data["thumbnail"] = img["thumbnail"]["src"]
            images.append(image_data)
    
    return BraveSearchSummary(
        title=title,
        content=content,
        query=query,
        sources=sources,
        images=images
    )


def create_brave_citation(summary: BraveSearchSummary) -> Citation:
    """
    Create a citation for Brave search results.
    
    Args:
        summary: BraveSearchSummary object
        
    Returns:
        Citation object for the search
    """
    # Format current date
    # current_date = datetime.now().strftime("%B %d, %Y")
    
    # Create citation content
    citation_content = f"{summary.title}\n"
    citation_content += f"Query: {summary.query}\n"
    # citation_content += f"Date: {current_date}\n\n"
    citation_content += f"{summary.content}\n\n"
    
    # Add sources if available
    if summary.sources:
        citation_content += "Sources:\n"
        # Format sources as numbered list in citation too
        for i, source in enumerate(summary.sources, 0):
            citation_content += f"{i}. {source.get('title', 'Unknown')}: {source.get('url', '')}\n"
    
    # Create and return citation
    return create_standard_citation(
        title=f"Brave Search: {summary.query}",
        url="https://search.brave.com",
        formatted_content=citation_content
    )


@tool
async def brave_search(query: str) -> RULAC_TOOL_RESULT:
    """
    Search the web using Brave Search and return summarized results with relevant sources.
    
    This tool is useful for:
    - Answering factual questions ("Who is the current president of France?")
    - Researching general topics ("Information about climate change agreements")
    - Finding current information not available in specialized databases
    - Getting summarized information with relevant sources cited
            
    Args:
        query: The search query, which can be a direct question or topic phrase
        
    Returns:
        RULAC_TOOL_RESULT with formatted search results and citations from web sources
    """
    tool_name = "brave_search"
    
    try:
        log.debug(f"Starting Brave search for query: {query}")
        
        # Execute the search query
        raw_results = await brave_search_query(query)
        
        if not raw_results:
            error_message = f"No results found for query: {query}"
            return format_standard_tool_result(
                content=error_message,
                citations=[],
                tool_name=tool_name,
                tool_params={"query": query},
                beacon_tool_source="BRAVE"
            )
        
        # Process the results
        summary = process_brave_summary(raw_results, query)
        
        # Create formatted content
        formatted_content = f"### {summary.title}\n\n"
        formatted_content += summary.content
        
        # Add sources if available
        if summary.sources:
            formatted_content += "\n\n#### Sources\n"
            # Display sources as a numbered list instead of bullet points
            for i, source in enumerate(summary.sources, 0):
                formatted_content += f"{i}. [{source.get('title', 'Source')}]({source.get('url', '')})\n"
        
        # Create citation
        citation = create_brave_citation(summary)
        
        # Return formatted result
        return format_standard_tool_result(
            content=formatted_content,
            citations=[citation],
            tool_name=tool_name,
            tool_params={"query": query},
            beacon_tool_source="BRAVE"
        )
        
    except Exception as e:
        error_message = f"Error in Brave search: {str(e)}"
        log.error(error_message)
        
        # Return error result
        return format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params={"query": query},
            beacon_tool_source="BRAVE"
        )


# Test function for direct execution
async def test_brave_search():
    """Test function to run the Brave search when the file is executed directly"""
    # test_query = "what is the highest mountain in the world?"
    test_query = "who is the voguer vinii revlon and what is his background?"
    
    # Call brave_search_query directly instead of using the decorated function
    log.debug(f"Starting test search for query: {test_query}")
    
    raw_results = await brave_search_query(test_query)
    
    if not raw_results:
        print("No results found for the test query")
        return
    
    # Process the results
    summary = process_brave_summary(raw_results, test_query)
    
    # Create formatted content
    formatted_content = f"### {summary.title}\n\n"
    formatted_content += summary.content
    
    # Add sources if available
    if summary.sources:
        formatted_content += "\n\n#### Sources\n"
        # Use numbered list in test function as well
        for i, source in enumerate(summary.sources, 0):
            formatted_content += f"{i}. {source.get('title', 'Source')}: {source.get('url', '')}\n"
    
    # Create citation
    citation = create_brave_citation(summary)
    
    print("\n" + "="*50)
    print(f"Test Query: {test_query}")
    print("="*50)
    
    print("\nContent:")
    print(formatted_content)
    
    print("\nCitation:")
    print(f"- {citation['title']}")
    print(f"  URL: {citation['url']}")
    
    print("="*50)


# Run test when executed directly
if __name__ == "__main__":
    asyncio.run(test_brave_search()) 