# Web_tools.py - Web search and scraping tools
from typing import List, Dict, Any, Union, Optional, TypedDict, Literal
from langchain_core.tools import tool
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import logging
import os
import coloredlogs
import requests
from langchain_community.document_loaders import PyPDFLoader
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import random

# Import standardized functions from RULAC_tools
from tools.RULAC_tools import (
    Citation, 
    RULAC_TOOL_RESULT,
    create_standard_citation, 
    format_standard_tool_result,
    standardized_tool_test,
    display_formatted_results
)

# Initialize fake user agent
ua = UserAgent()

# Common headers that we'll rotate through
COMMON_HEADERS = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "no-cache"
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache"
    }
]

def get_request_headers(custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Generate random headers for HTTP requests, optionally merging with custom headers.
    
    Args:
        custom_headers: Optional dictionary of custom headers to merge with defaults
        
    Returns:
        Dictionary of headers to use for the request
    """
    # Get a random user agent
    user_agent = ua.random
    
    # Get a random set of common headers
    base_headers = random.choice(COMMON_HEADERS).copy()
    
    # Add the random user agent
    base_headers["User-Agent"] = user_agent
    
    # Merge with custom headers if provided
    if custom_headers:
        base_headers.update(custom_headers)
    
    return base_headers

# Global configuration values
tool_specific_values = {
    "SEARXNG_ENGINE_API_BASE_URL": "http://searxng:8080/search",
    "SEARXNG_ENGINE_API_TESTING_BASE_URL": "http://localhost:8081/search",
    "IGNORED_WEBSITES": "",
    "RETURNED_SCRAPPED_PAGES_NO": 3,
    "SCRAPPED_PAGES_NO": 3,
    "PAGE_CONTENT_WORDS_LIMIT": 2000,
    "CITATION_LINKS": True,
    "WHITELISTED_SITES": [
        # {
        #     "name": "NY Post",
        #     "url": "nypost.com",
        #     "most_relevant_topic": "latest news"
        # },
        {
            "name": "BBC",
            "url": "bbc.com/news",
            "most_relevant_topic": "latest news"
        },
        {
            "name": "ICRC Blog",
            "url": "blogs.icrc.org",
            "most_relevant_topic": "international humanitarian law (IHL) and policy"
        },
        # {
        #     "name": "Human Rights Watch",
        #     "url": "hrw.org",
        #     "most_relevant_topic": "human rights"           
        # },
        # {
        #     "name": "Wikipedia",
        #     "url": "wikipedia.org",
        #     "most_relevant_topic": "general knowledge"
        # }
    ]
}

# Initialize Rich Console for formatted output
console = Console()

# Configure logging
logger = logging.getLogger("Beacon.Web")
coloredlogs.install(
    logger=logger,
    level="DEBUG",
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
)

# Define log styles for rich console output
LOG_STYLES = {
    "info": {"style": "black on yellow", "border_style": "yellow"},
    "success": {"style": "black on green", "border_style": "green"},
    "error": {"style": "white on red", "border_style": "red"},
    "title": {"style": "bold white on green", "border_style": "green"}
}

def log(message, level="info", as_panel=True):
    """
    Log a message with consistent styling based on level.
    
    Args:
        message: The message to log
        level: The log level (info, success, error, title)
        as_panel: Whether to format as a panel or simple text
    """
    style = LOG_STYLES.get(level, LOG_STYLES["info"])
    
    if as_panel:
        console.print(Panel(message, **style))
    else:
        console.print(message, style=style["style"])

# Helper functions
def get_base_url(url):
    """Extract base URL (domain) from full URL."""
    parsed = urlparse(url)
    return parsed.netloc

def remove_emojis(text):
    """Remove emojis from text."""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emojis
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def generate_excerpt(content, max_length=200):
    """Generate a short excerpt from content for display purposes."""
    if not content:
        return ""
    
    # Remove extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    # If content is shorter than max_length, return as is
    if len(content) <= max_length:
        return content
    
    # Otherwise, truncate to max_length and add "..."
    return content[:max_length] + "..."

def truncate_to_n_words(text, token_limit):
    """Truncate text to specified number of words."""
    words = text.split()
    if len(words) <= token_limit:
        return text
    return " ".join(words[:token_limit])

async def get_search_results(query, engine_api_base_url, number_of_results=10):
    """
    Get search results from the SearXNG search engine API.
    
    Args:
        query: The search query string
        engine_api_base_url: The base URL for the search engine API
        number_of_results: Maximum number of results to return
        
    Returns:
        List of search result dictionaries
    """
    try:
        log(f"Connecting to search engine at {engine_api_base_url}")
        
        # Set up query parameters
        params = {
            "q": query,
            "format": "json",
            "number_of_results": number_of_results,
        }
        
        # Generate headers for this request
        headers = get_request_headers()
        
        # Send the request to the search engine
        resp = requests.get(
            engine_api_base_url, params=params, headers=headers, timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Extract results
        results = data.get("results", [])
        log(f"Found {len(results)} search results", "success")
        return results
        
    except requests.exceptions.RequestException as e:
        log(f"Search engine error: {str(e)}", "error")
        return []

async def async_scrape(
    urls: List[str],
    ignored_websites: str = "",
    scrapped_pages_no: int = 5,
    page_content_words_limit: int = 2000,
    debug: bool = False
) -> List[str]:
    """
    Asynchronously scrape multiple URLs using requests.
    
    Args:
        urls: List of URLs to scrape
        ignored_websites: Comma-separated list of websites to ignore
        scrapped_pages_no: Maximum number of pages to scrape
        page_content_words_limit: Maximum number of words per page
        debug: Whether to print debug information
        
    Returns:
        List of scraped page contents
    """
    # Initialize results
    pages_content = []
    
    # Process ignored websites
    ignored_websites_list = [site.strip() for site in ignored_websites.split(",") if site.strip()]
    
    # Process each URL
    for url in urls:
        try:
            # Check if URL should be ignored
            base_url = get_base_url(url)
            if any(ignored in base_url for ignored in ignored_websites_list):
                if debug:
                    log(f"Skipping ignored website: {url}", "info", False)
                pages_content.append("")
                continue
                
            if debug:
                log(f"Scraping URL: {url}", "info", False)
                
            # Generate headers for this request
            headers = get_request_headers()
                
            # Fetch the page content
            response = requests.get(url, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Special handling for BBC News articles
            if "bbc.com/news" in url:
                if debug:
                    log(f"Processing BBC News article: {url}", "info", False)
                
                # Find the main article content
                article = soup.find("article")
                if article:
                    # Remove script, style elements and other unwanted tags
                    for tag in article.find_all([
                        "script", 
                        "style", 
                        "aside", 
                        "nav", 
                        "header", 
                        "footer", 
                        "button", 
                        "div[data-component='tags']", 
                        "span[data-testid='card-metadata-tag']",
                        "div[data-component='headline-block']",
                        "div[data-testid='byline-new-contributors']",
                        "ul.sc-5c9c90b0-0",  # Article links section
                        "div[data-component='tags']"  # Tags section
                    ]):
                        tag.decompose()
                    
                    # Get the text content with better formatting
                    text = article.get_text(separator="\n", strip=True)
                    
                    # Clean up the text
                    text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove excessive newlines
                    text = re.sub(r'\s+', ' ', text)  # Clean up spaces
                    text = text.strip()
                    
                    if debug:
                        log(f"Successfully extracted BBC article content", "success", False)
                else:
                    if debug:
                        log(f"No article tag found in BBC page, falling back to standard extraction", "info", False)
                    # Fall back to standard extraction if no article tag found
                    for script in soup(["script", "style"]):
                        script.decompose()
                    for sup in soup.find_all(['sup']):
                        sup.decompose()
                    text = soup.get_text(separator=" ", strip=True)
            else:
                # Standard extraction for non-BBC sites
                for script in soup(["script", "style"]):
                    script.decompose()
                for sup in soup.find_all(['sup']):
                    sup.decompose()
                text = soup.get_text(separator=" ", strip=True)
            
            # Clean up the text
            text = re.sub(r'\(/wiki/[^)]+\)', '', text)  # Remove wiki-style links
            text = re.sub(r'\(https?://[^)]+\)', '', text)  # Remove URLs in parentheses
            text = re.sub(r'\[\s*\d+\s*\(#cite[^]]+\)\s*\]', '', text)  # Remove citation references
            text = re.sub(r'https?://\S+', '', text)  # Remove remaining URLs
            text = re.sub(r'\s+', ' ', text).strip()  # Clean up spaces
            
            # Limit to specified number of words
            if page_content_words_limit > 0:
                words = text.split()
                if len(words) > page_content_words_limit:
                    text = " ".join(words[:page_content_words_limit])
                    if debug:
                        log(f"Truncated content to {page_content_words_limit} words", "info", False)
            
            # Add the content to the results
            pages_content.append(text)
            
            if debug:
                log(f"Successfully scraped: {url}", "success", False)
                
        except Exception as e:
            if debug:
                log(f"Error scraping {url}: {str(e)}", "error", False)
            # Add empty content for failed scrapes
            pages_content.append("")
    
    return pages_content

@tool
async def get_website(
    url: str,
    doc_type: str = "html",
) -> RULAC_TOOL_RESULT:
    """
    Fetches and processes content from a specified URL.
    
    For HTML pages, it extracts the main content, removing navigation elements and irrelevant parts.
    For PDFs, it extracts and processes all text content.
    Use this tool when you need to extract information from a specific website or document.
    
    :param url: URL of the web page or PDF to retrieve
    :param doc_type: Type of document to retrieve (either "html" or "pdf")
    :return: A dictionary with "content" containing processed content from the URL and "citations" list
    """
    
    # Print start marker for tool execution
    console.print("\n[bold white]" + "="*50 + "\n" + 
                 "STARTING TOOL: get_website\n" + 
                 "="*50 + "[/bold white]\n")
    
    # Set up tool metadata for result
    tool_name = "get_website"
    tool_params = {
        "url": url,
        "doc_type": doc_type,
        "query": f"Retrieve content from {url}"
    }
    
    try:
        log(f"Loading website contents from URL: {url}")
        content = ""
        title = url  # Default title is the URL
        citations = []

        # For regular web pages
        if doc_type.lower() == "html":
            try:
                log(f"Retrieving HTML content from {url}")
                content_list = await async_scrape(
                    [url],
                    ignored_websites="",
                    scrapped_pages_no=1,
                    page_content_words_limit=tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"],
                    debug=True
                )
                content = content_list[0] if content_list else ""
                
                # Try to extract the title from the page
                try:
                    response = requests.get(url, headers=get_request_headers(), timeout=10)
                    soup = BeautifulSoup(response.text, "html.parser")
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()
                except Exception:
                    # If title extraction fails, just use the URL as title
                    pass
                    
                log(f"Successfully retrieved HTML content", "success")
            except Exception as e:
                error_msg = f"Error while scraping HTML: {str(e)}"
                log(error_msg, "error")
                
                # Print end marker for tool execution
                console.print("\n[bold white]" + "="*50 + "\n" + 
                             "ENDING TOOL: get_website (with error)\n" + 
                             "="*50 + "[/bold white]\n")
                             
                # Return formatted error result
                return format_standard_tool_result(
                    content=f"Failed to retrieve content from {url}: {str(e)}",
                    citations=[],
                    tool_name=tool_name,
                    tool_params=tool_params,
                    beacon_tool_source="WEB"
                )

        # For PDF documents
        elif doc_type.lower() == "pdf":
            try:
                log(f"Retrieving PDF content from {url}")
                loader = PyPDFLoader(url)
                documents = loader.load_and_split()
                
                # Extract text from PDF documents
                pdf_text = ""
                for doc in documents:
                    pdf_text += doc.page_content + "\n\n"
                
                # Truncate PDF content to the word limit
                original_word_count = len(pdf_text.split())
                pdf_text = truncate_to_n_words(pdf_text, tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"])
                if len(pdf_text.split()) < original_word_count:
                    log(f"Truncated PDF content from {original_word_count} to {tool_specific_values['PAGE_CONTENT_WORDS_LIMIT']} words", "info")
                
                content = pdf_text
                
                # Try to extract a title from the URL path
                path = urlparse(url).path
                if path:
                    filename = os.path.basename(path)
                    if filename:
                        title = filename
                
                log(f"Successfully retrieved PDF content", "success")
            except Exception as e:
                error_msg = f"Error while scraping PDF: {str(e)}"
                log(error_msg, "error")
                
                # Print end marker for tool execution
                console.print("\n[bold white]" + "="*50 + "\n" + 
                             "ENDING TOOL: get_website (with error)\n" + 
                             "="*50 + "[/bold white]\n")
                             
                # Return formatted error result
                return format_standard_tool_result(
                    content=f"Failed to retrieve PDF content from {url}: {str(e)}",
                    citations=[],
                    tool_name=tool_name,
                    tool_params=tool_params,
                    beacon_tool_source="WEB"
                )
        else:
            error_msg = f"Unsupported document type: {doc_type}. Supported types are 'html' and 'pdf'."
            log(error_msg, "error")
            
            # Print end marker for tool execution
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         "ENDING TOOL: get_website (invalid document type)\n" + 
                         "="*50 + "[/bold white]\n")
                         
            # Return formatted error result
            return format_standard_tool_result(
                content=error_msg,
                citations=[],
                tool_name=tool_name,
                tool_params=tool_params,
                beacon_tool_source="WEB"
            )

        # Create citation for this website
        citation = create_standard_citation(
            title=title,
            url=url,
            formatted_content=content
        )
        citations.append(citation)
        
        # Display formatted results
        display_formatted_results(
            cleaned_tool_message=content,
            title="WEB CONTENT RETRIEVAL RESULTS",
            tool_name=tool_name,
            tool_params=tool_params,
            citations=citations,
            beacon_tool_source="WEB",
            showFull=True
        )
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     "ENDING TOOL: get_website (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return standardized result format
        return format_standard_tool_result(
            content=content,
            citations=citations,
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="WEB"
        )
        
    except Exception as e:
        error_message = f"Error retrieving website content: {e}"
        log(error_message, "error")
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     "ENDING TOOL: get_website (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return formatted error result
        return format_standard_tool_result(
            content=f"Error retrieving content from {url}: {error_message}",
            citations=[],
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="WEB"
        )

# Extract URLs from WHITELISTED_SITES for type checking
WHITELISTED_SITE_URLS = [site["url"] for site in tool_specific_values["WHITELISTED_SITES"]]

# For type checking purposes
from typing import get_args

# Create a Literal type for allowed sites
# We need to use this approach because Literal requires constant values known at compile time
WhitelistedSiteLiteral = Literal["nypost.com", "bbc.com/news", "hrw.org", "wikipedia.org", "blogs.icrc.org"]

# Generate a static description for the whitelist sites that will be used in the docstring
WHITELIST_SITES_DOC = "Determine the most relevant web source from this site list based on the query:\n"
for site in tool_specific_values["WHITELISTED_SITES"]:
    WHITELIST_SITES_DOC += f"- {site['url']} ({site['most_relevant_topic']})\n"

@tool
async def brave_search(
    query: str,
    site: WhitelistedSiteLiteral
) -> RULAC_TOOL_RESULT:
    """
    Search the web for information using SearXNG search engine.
    Returns relevant page content from multiple sources.

    Use this tool when you need up-to-date information about any topic,
    such as recent developments, news, or general information that may not
    be available in your knowledge base.
    
    WHITELIST_SITES_PLACEHOLDER
    
    :param query: The search query to look for on the web
    :param site: Most relevant website to search within (must be one of the allowed sites)
    :return: A dictionary with "content" string containing search results and "citations" list
    """
    
    # Print start marker for tool execution
    console.print("\n[bold white]" + "="*50 + "\n" + 
                 "STARTING TOOL: brave_search\n" + 
                 "="*50 + "[/bold white]\n")
    
    # Set up tool metadata for result
    tool_name = "brave_search"
    tool_params = {
        "query": query,
        "site": site
    }
    
    try:
        # Validate that the site is in the allowed list if provided
        if site and site not in get_args(WhitelistedSiteLiteral):
            allowed_sites = ", ".join(str(s) for s in get_args(WhitelistedSiteLiteral))
            error_message = f"Invalid site '{site}'. Must be one of: {allowed_sites}"
            log(error_message, "error")
            
            # Print end marker for tool execution
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         "ENDING TOOL: brave_search (with error)\n" + 
                         "="*50 + "[/bold white]\n")
            
            # Return formatted error result
            return format_standard_tool_result(
                content=error_message,
                citations=[],
                tool_name=tool_name,
                tool_params=tool_params,
                beacon_tool_source="WEB"
            )
            
        # Modify query to include site if specified
        search_query = query
        if site:
            search_query = f"site:{site} {query}"
            log(f"🔍 Searching {site} for: {query}")
        else:
            log(f"🔍 Searching web for: {query}")
        
        # Determine which API endpoint to use based on environment
        if os.path.exists("/app/backend/beacon_code"):
            engine_api_base_url = tool_specific_values["SEARXNG_ENGINE_API_BASE_URL"]
        else:
            engine_api_base_url = tool_specific_values["SEARXNG_ENGINE_API_TESTING_BASE_URL"]

        # Get search results from SearXNG
        search_results = await get_search_results(
            query=search_query,
            engine_api_base_url=engine_api_base_url
        )
        
        # Initialize containers for results
        results_list = []
        formatted_results = []
        citations = []
        
        if search_results:
            log(f"Processing {len(search_results)} search results")
            
            # Filter out ignored websites
            ignored_websites_list = tool_specific_values["IGNORED_WEBSITES"].split(",") if tool_specific_values["IGNORED_WEBSITES"] else []
            filtered_results = [
                r for r in search_results
                if not any(ignored in r["url"] for ignored in ignored_websites_list)
            ]
            
            # Limit number of pages to scrape
            filtered_results = filtered_results[:tool_specific_values["SCRAPPED_PAGES_NO"]]
            
            # Get URLs from filtered results
            urls = [r["url"] for r in filtered_results]
            
            try:
                log(f"Scraping content from {len(urls)} pages")
                pages_content = await async_scrape(
                    urls,
                    ignored_websites=tool_specific_values["IGNORED_WEBSITES"],
                    scrapped_pages_no=tool_specific_values["SCRAPPED_PAGES_NO"],
                    page_content_words_limit=tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"],
                    debug=True
                )
                
                # Process and format results
                for i, (url, title, content) in enumerate(zip(urls, [r["title"] for r in filtered_results], pages_content)):
                    if not content:
                        continue
                    
                    # Add to results list
                    results_list.append({
                        "url": url,
                        "title": title,
                        "content": content
                    })
                    
                    # Format for output
                    formatted_results.append(
                        f"## {i+1}. {title}\n"
                        f"URL: {url}\n\n"
                        f"{content}"
                    )
                    
                    # Create citation using standard format
                    citation = create_standard_citation(
                        title=title if title else f"Web content from {url}",
                        url=url,
                        formatted_content=content
                    )
                    citations.append(citation)
                
                # Limit number of returned pages
                max_results = tool_specific_values["RETURNED_SCRAPPED_PAGES_NO"]
                results_list = results_list[:max_results]
                formatted_results = formatted_results[:max_results]
                citations = citations[:max_results]
                
            except Exception as e:
                log(f"Error during page scraping: {str(e)}", "error")
        else:
            log("No search results found", "error")
        
        log(f"Search complete. Found {len(results_list)} relevant pages", "success")
        
        # Prepare the final content
        site_info = f" on {site}" if site else ""
        final_content = f"# Web Search Results for: {query}{site_info}\n\n" + "\n---\n".join(formatted_results)
        
        # Display formatted results
        display_formatted_results(
            cleaned_tool_message=final_content if formatted_results else "No relevant information found for your query.",
            title="WEB SEARCH RESULTS",
            tool_name=tool_name,
            tool_params=tool_params,
            citations=citations,
            beacon_tool_source="WEB",
            showFull=True
        )
        
        # Return no results if none found
        if not formatted_results:
            # Print end marker for tool execution
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         "ENDING TOOL: brave_search (no results)\n" + 
                         "="*50 + "[/bold white]\n")
                         
            # Return formatted empty result
            return format_standard_tool_result(
                content="No relevant information found for your query.",
                citations=[],
                tool_name=tool_name,
                tool_params=tool_params,
                beacon_tool_source="WEB"
            )
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     "ENDING TOOL: brave_search (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return standardized result
        return format_standard_tool_result(
            content=final_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="WEB"
        )
    
    except Exception as e:
        error_message = f"Error during web search: {str(e)}"
        log(error_message, "error")
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     "ENDING TOOL: brave_search (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return formatted error result
        return format_standard_tool_result(
            content=f"Error searching the web: {str(e)}",
            citations=[],
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="WEB"
        )

# Dynamically update the docstring at import time
brave_search.__doc__ = brave_search.__doc__.replace("WHITELIST_SITES_PLACEHOLDER", WHITELIST_SITES_DOC)

if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        """Run all test functions"""
        log("STARTING WEB TOOLS TESTS", "title")
        
        # Run test functions using standardized test framework

        websearch_test_scenarios = [
            # {
            #     "name": "Web Search on RULAC Website",
            #     "params": {
            #         "query": "who is RULAC and how do they classify conflicts?",
            #     },
            # },
            # {
            #     "name": "Latest News on Conflict",
            #     "params": {
            #         "query": "latest information on Ukraine conflict classification",
            #     },
            # },
            # {
            #     "name": "Site-specific Search",
            #     "params": {
            #         "query": "Ukraine conflict",
            #         "site": "bbc.com/news"
            #     },
            # },
            # {
            #     "name": "Site-specific Search: BBC News",
            #     "params": {
            #         "query": "What IHL applies to the Ukraine conflict?",
            #         "site": "bbc.com/news"
            #     },
            # },
            {
                "name": "Site-specific Search: ICRC Blog",
                "params": {
                    "query": "somalia",
                    "site": "blogs.icrc.org"
                },
            },
            # {
            #     "name": "Site-specific Search: NY Post",
            #     "params": {
            #         "query": "Ukraine conflict",
            #         "site": "nypost.com"
            #     },
            # },
            # {
            #     "name": "Site-specific Search: Human Rights Watch",
            #     "params": {
            #         "query": "Ukraine conflict",
            #         "site": "hrw.org"
            #     },
            # }
        ]

# for latest news on a topic
# !news site:https://www.thenewhumanitarian.org ATMIS (Humanitarian aid, humanitarian policy, humanitarian news)
# !news site:https://www.bbc.com/news/articles ethiopia and eritrea war (top 3 articles)
# !news site:https://www.bbc.com/news/articles ukraine ceasefire (articles need to be mentioned or we get live feeds) (top 3 articles)
# !news site:https://www.hrw.org/news ukraine (note only country needs to be mentioned)

# for a get human rights report by country
#  gets the latest hrw human rights country report site:https://www.hrw.org/news ukraine 

        get_website_url_test_scenarios = [
            {
                "name": "HTML Page Retrieval",
                "params": {
                    "url": "https://www.bbc.com/news/topics/cx1m7zg0gzdt",
                    "doc_type": "html"
                },
            },
            {
                "name": "PDF Document",
                "params": {
                    "url": "https://www.icrc.org/sites/default/files/external/doc/en/assets/files/other/irrc-873-vite.pdf",
                    "doc_type": "pdf"
                },
            },
        ]


        # Use the standardized test framework
        await standardized_tool_test(
            tool_function=brave_search,
            test_scenarios=websearch_test_scenarios,
            test_title="Brave Web Search Tool Test"
        )

        # # Use the standardized test framework
        # await standardized_tool_test(
        #     tool_function=get_website,
        #     test_scenarios=get_website_url_test_scenarios,
        #     test_title="Website Content Retrieval Tool Test"
        # )

        log("ALL TESTS COMPLETED", "success")
    
    # Run the async test function
    asyncio.run(run_tests()) 