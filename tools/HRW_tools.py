from typing import List, Dict, Any, Union, Optional, TypedDict, Literal
from langchain_core.tools import tool
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import logging
import os
import coloredlogs
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import pprint
import json
from datetime import datetime
from fake_useragent import UserAgent
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

# Global configuration values
# NOTE: API keys should be set via environment variables or passed from the pipeline's Valves
tool_specific_values = {
    "BRAVE_SEARCH_API_BASE_URL": "https://api.search.brave.com/res/v1/web/search",
    "BRAVE_SEARCH_API_KEY": os.getenv("BRAVE_SEARCH_API_KEY", ""),
    "PAGE_CONTENT_WORDS_LIMIT": 4000,
}

# Initialize fake user agent
ua = UserAgent()

# Global logging control flag
LOGGING_ENABLED = False

# Common headers that we'll rotate through
COMMON_HEADERS = [
    {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": tool_specific_values["BRAVE_SEARCH_API_KEY"]
    }
]

def set_brave_api_key(api_key: str):
    """
    Set Brave API key dynamically from the pipeline's Valves system.
    Updates both the global config and headers.
    
    Args:
        api_key: Brave Search API key
    """
    global COMMON_HEADERS
    tool_specific_values["BRAVE_SEARCH_API_KEY"] = api_key
    COMMON_HEADERS = [
        {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
    ]

def get_request_headers(custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Generate headers for HTTP requests, optionally merging with custom headers.
    
    Args:
        custom_headers: Optional dictionary of custom headers to merge with defaults
        
    Returns:
        Dictionary of headers to use for the request
    """
    # Get a random user agent
    user_agent = ua.random
    logger.debug(f"Generated User-Agent: {user_agent}")
    
    # Get a random set of common headers
    base_headers = random.choice(COMMON_HEADERS).copy()
    
    # Add the random user agent
    base_headers["User-Agent"] = user_agent
    
    # Merge with custom headers if provided
    if custom_headers:
        base_headers.update(custom_headers)
    
    return base_headers

# Initialize Rich Console for formatted output
console = Console()

# Configure logging
logger = logging.getLogger("Beacon.HRW")
coloredlogs.install(
    logger=logger,
    level="INFO",
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
    if not LOGGING_ENABLED:
        return
    
    # Map custom log levels to standard logging levels
    log_level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "success": logging.INFO,
        "error": logging.ERROR,
        "title": logging.INFO
    }
    
    # Get the standard logging level for this message
    std_level = log_level_map.get(level, logging.INFO)
    
    # Only display if the current logger level is less than or equal to this message's level
    if logger.isEnabledFor(std_level):
        style = LOG_STYLES.get(level, LOG_STYLES["info"])
        
        if as_panel:
            console.print(Panel(message, **style))
        else:
            console.print(message, style=style["style"])

async def async_scrape_hrw_report(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Asynchronously scrape multiple URLs using requests.
    
    Args:
        urls: List of URLs to scrape
        
    Returns:
        List of dictionaries containing page content and metadata
    """
    # Create temp directory if it doesn't exist
    temp_dir = "temp_test_data"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Initialize results
    pages_data = []
    
    # Process each URL
    for url in urls:
        try:
            logger.debug(f"Scraping URL: {url}")
                
            # Generate headers for this request
            headers = get_request_headers()
                
            # Fetch the page content
            response = requests.get(url, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract article modification date from meta tags
            article_date = None
            for meta in soup.find_all("meta"):
                if meta.get("property") == "article:modified_time":
                    article_date = meta.get("content")
                    break
            
            logger.debug(f"Found article date: {article_date}")
            
            # Save raw HTML and soup data for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            url_safe = re.sub(r'[^a-zA-Z0-9]', '_', url)
            filename = os.path.join(temp_dir, f"hrw_scrape_{url_safe}_{timestamp}")
            
            # # Save raw HTML
            # with open(f"{filename}_raw.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)
            
            # Look for the main article content container
            article_content = soup.find('article')
            if article_content:
                # Remove sharing buttons and other non-content elements
                for element in article_content.find_all(['div', 'aside'], class_=['share-buttons', 'social-sharing', 'sidebar']):
                    element.decompose()
                
                # Remove navigation elements
                for nav in article_content.find_all('nav'):
                    nav.decompose()
                
                # Remove header section with image and caption
                header = article_content.find('div', class_='chapter-header')
                if header:
                    header.decompose()
                
                # Remove article info section (contains sharing buttons, etc)
                article_info = article_content.find('div', class_='article__info')
                if article_info:
                    article_info.decompose()
                
                # Find the main article body - this should contain just the report text
                article_body = article_content.find('div', class_='article-body')
                if article_body:
                    main_content = article_body
                else:
                    main_content = article_content
            
            if not main_content:
                # Fallback: try to find content by class or role
                main_content = soup.find('div', role='main') or soup.find('main')
            
            if not main_content:
                # Last resort: try to find content by common content class names
                main_content = soup.find('div', class_=['content', 'article-content', 'main-content'])
            
            # Get the text content from the main content area
            if main_content:
                logger.debug("Found main content container")
                
                # Remove unwanted elements
                for tag in main_content.find_all(["script", "style", "nav", "header", "footer", "button"]):
                    tag.decompose()
                
                # Process paragraphs and headers to preserve structure
                paragraphs = []
                
                for element in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    # Process all text nodes and links within the element to ensure proper spacing
                    text_parts = []
                    for content in element.contents:
                        if content.name == 'a':  # If it's a link
                            text_parts.append(' ' + content.get_text(strip=True) + ' ')
                        elif content.string:  # If it's a text node
                            text_parts.append(content.string.strip())
                    
                    # Join all parts and normalize spaces
                    text = ' '.join(text_parts)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    if text:  # Only add non-empty paragraphs
                        # Check if this is a header and convert it to markdown format
                        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            # Always convert to h4 (####) regardless of original level
                            text = '#### ' + text
                        paragraphs.append(text)
                
                # Join paragraphs with double newlines to preserve structure
                text = '\n\n'.join(paragraphs)
                
                # Clean up the text
                text = re.sub(r'[ \t]+', ' ', text)  # Clean up only spaces and tabs, preserve newlines
                text = re.sub(r'\s+([,\.])', r'\1', text)  # Remove spaces before punctuation
                
                text = re.sub(r'Share this via \w+\s*', '', text)  # Remove sharing text
                text = re.sub(r'More sharing options\s*', '', text)  # Remove more sharing text
                text = text.strip()
                
            else:
                text = ""
                logger.warning("Could not find main content container")
            
            # Log text statistics
            logger.debug(f"Text length before truncation: {len(text.split())} words")
            
            # Limit to specified number of words
            words = text.split()
            if len(words) > tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"]:
                text = " ".join(words[:tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"]])
                logger.debug(f"Truncated content to {tool_specific_values['PAGE_CONTENT_WORDS_LIMIT']} words")
                logger.debug(f"Text length after truncation: {len(text.split())} words")
            
            # Add the content and metadata to the results
            pages_data.append({
                "content": text,
                "article_date": article_date
            })
            
            logger.debug(f"Successfully scraped: {url}")
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Add empty content for failed scrapes
            pages_data.append({"content": "", "article_date": None})
    
    return pages_data

async def get_search_results(query: str, number_of_results: int = 1) -> List[Dict[str, Any]]:
    """
    Get search results from the Brave Search API.
    
    Args:
        query: The search query string
        number_of_results: Maximum number of results to return
        
    Returns:
        List of search result dictionaries
    """
    try:
        log(f"Connecting to Brave Search API", "debug")
        
        # Set up query parameters
        params = {
            "q": query,
            "count": number_of_results,
            "search_lang": "en",
            "ui_lang": "en-US",
            "safesearch": "off",
            "text_decorations": "1",
            "spellcheck": "1",
            "freshness": "2023-07-27to2025-03-28"  # Filter for reports from 2023 to 2025
        }
        
        # Generate headers for this request
        headers = get_request_headers()
        
        # Send the request to the Brave Search API
        resp = requests.get(
            tool_specific_values["BRAVE_SEARCH_API_BASE_URL"],
            params=params,
            headers=headers,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Extract results from Brave Search response
        results = []
        if "web" in data and "results" in data["web"]:
            for result in data["web"]["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "link": result.get("url", ""),
                    "snippet": result.get("description", ""),
                    "category": "web"
                })
        
        log(f"Found {len(results)} search results", "success")
        return results
        
    except requests.exceptions.RequestException as e:
        log(f"Search engine error: {str(e)}", "error")
        return []

@tool
async def get_human_rights_research_by_country(country: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves the latest human rights research for a specific country, including human rights violations and conditions.
    
    :param country: The name of the country to get human rights information for
    :return: A dictionary with "content" containing the report content and "citations" list
    """
    
    # Print start marker for tool execution
    if LOGGING_ENABLED:
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     "STARTING TOOL: get_human_rights_research_by_country\n" + 
                     "="*50 + "[/bold white]\n")
    
    # Set up tool metadata for result
    tool_name = "get_human_rights_research_by_country"
    research_task = f"Human Rights Watch (HRW) country report for {country}"
    tool_params = {
        "country": country,
        "research_task": research_task
    }
    
    try:
        # Construct the search query
        # create variable for current year and previous year to ensure the latest report is retrieved
        current_year = datetime.now().year
        # previous_year = current_year - 1
        search_query = f'site:https://www.hrw.org/world-report {country} World Report {current_year}'
        log(f"Searching HRW for reports about: {country}", "debug")
        log(f"Search query: {search_query}", "debug")
        
        # Get search results from Brave Search
        search_results = await get_search_results(
            query=search_query,
            number_of_results=1  # only return 1 result which should be the latest report
        )
        
        # Pretty print the results for debugging
        log("Search Results:", "debug")
        for i, result in enumerate(search_results, 1):
            log(f"\nResult {i}:", "debug", False)
            log(f"Title: {result.get('title', 'No title')}", "debug", False)
            log(f"Link: {result.get('link', 'No link')}", "debug", False)
            log(f"Snippet: {result.get('snippet', 'No snippet')}", "debug", False)
            log(f"Category: {result.get('category', 'No category')}", "debug", False)
            log("-" * 50, "debug", False)
            # # print the result to the console
            # print(result)
        
        # Initialize containers for results
        results_list = []
        formatted_results = []
        citations = []
        
        if search_results:
            log(f"Processing {len(search_results)} search results", "debug")
            
            # Get URLs from results
            urls = [r["link"] for r in search_results]
            
            try:
                log(f"Scraping content from {len(urls)} pages", "debug")
                pages_data = await async_scrape_hrw_report(
                    urls
                )
                
                # Process and format results
                for i, (url, title, page_data) in enumerate(zip(urls, [r["title"] for r in search_results], pages_data)):
                    if not page_data["content"]:
                        continue
                    
                    # Add to results list
                    results_list.append({
                        "url": url,
                        "title": title,
                        "content": page_data["content"],
                        "article_date": page_data["article_date"]
                    })
                    
                    # Format for output
                    date_str = ""
                    if page_data["article_date"]:
                        try:
                            # Parse the ISO format date and convert to human readable format
                            date_obj = datetime.fromisoformat(page_data["article_date"].replace("Z", "+00:00"))
                            date_str = f" (Publication date: {date_obj.strftime('%b %d, %Y')})"
                        except ValueError:
                            # Fallback if date parsing fails
                            date_str = f" (Publication date: {page_data['article_date']})"
                    formatted_results.append(
                        f"{title}{date_str}\n\n"
                        f"{page_data['content']}"
                    )
                    
                    # Create citation using standard format
                    citation = create_standard_citation(
                        title=title if title else f"HRW Report about {country}",
                        url=url,
                        formatted_content=page_data["content"]
                    )
                    citations.append(citation)
                
            except Exception as e:
                log(f"Error during page scraping: {str(e)}", "error")
        else:
            log("No search results found", "error")
        
        log(f"Search complete. Found {len(results_list)} relevant HRW report for {country}", "success")
        
        # Prepare the final content for prompt
        final_content = f"### Latest Human Rights Watch (HRW) Country Report for {country}\n\n" + "\n---\n".join(formatted_results)
        
        # Display formatted results
        display_formatted_results(
            cleaned_tool_message=final_content if formatted_results else "No relevant HRW reports found for this country.",
            title="HRW REPORTS",
            tool_name=tool_name,
            tool_params=tool_params,
            citations=citations,
            beacon_tool_source="HRW",
            showFull=False
        )
        
        # Return no results if none found
        if not formatted_results:
            # Print end marker for tool execution
            if LOGGING_ENABLED:
                console.print("\n[bold white]" + "="*50 + "\n" + 
                             "ENDING TOOL: get_human_rights_research_by_country (no results)\n" + 
                             "="*50 + "[/bold white]\n")
                         
            # Return formatted empty result
            return format_standard_tool_result(
                content="No relevant HRW reports found for this country.",
                citations=[],
                tool_name=tool_name,
                tool_params=tool_params,
                beacon_tool_source="HRW"
            )
        
        # Print end marker for tool execution
        if LOGGING_ENABLED:
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         "ENDING TOOL: get_human_rights_research_by_country (success)\n" + 
                         "="*50 + "[/bold white]\n")
        
        # Return standardized result
        return format_standard_tool_result(
            content=final_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="HRW"
        )
    
    except Exception as e:
        error_message = f"Error retrieving HRW reports: {str(e)}"
        log(error_message, "error")
        
        # Print end marker for tool execution
        if LOGGING_ENABLED:
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         "ENDING TOOL: get_human_rights_research_by_country (with error)\n" + 
                         "="*50 + "[/bold white]\n")
        
        # Return formatted error result
        return format_standard_tool_result(
            content=f"Error retrieving HRW reports: {str(e)}",
            citations=[],
            tool_name=tool_name,
            tool_params=tool_params,
            beacon_tool_source="HRW"
        )

if __name__ == "__main__":
    import asyncio
    
    # Enable logging for local testing so we can see the output
    # Directly modify the module-level variable
    import sys
    current_module = sys.modules[__name__]
    current_module.LOGGING_ENABLED = True
    # Set logger to DEBUG level to see detailed output
    logger.setLevel(logging.DEBUG)
    print("✓ Logging enabled for local testing (DEBUG level)\n")
    
    # Load environment variables from .env file for local testing
    try:
        from dotenv import load_dotenv
        # Try to load from parent directory (where .env should be)
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)  # Force override system env vars
            print(f"✓ Loaded .env file from: {env_path} (with override)")
        else:
            # Try current directory
            load_dotenv(override=True)  # Force override system env vars
            print("✓ Attempted to load .env from current directory (with override)")
        
        # Update Brave API key with loaded environment variable
        loaded_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        if loaded_key:
            set_brave_api_key(loaded_key)
            print(f"✓ Brave API key loaded successfully (length: {len(loaded_key)})")
        else:
            print("⚠ Warning: BRAVE_SEARCH_API_KEY not found in environment")
            
    except ImportError:
        print("⚠ Warning: python-dotenv not installed. Install with: pip install python-dotenv")
        print("  Or export environment variables manually before running")
    
    async def run_tests():
        """Run all test functions"""
        log("STARTING HRW TOOLS TESTS", "title")
        
        # Test scenarios
        hrw_test_scenarios = [
            {
                "name": "Get HRW Report for Russia",
                "params": {
                    "country": "Russia"
                },
            },
            # {
            #     "name": "Get HRW Report for USA",
            #     "params": {
            #         "country": "USA"
            #     },
            # },
            # {
            #     "name": "Get HRW Report for China",
            #     "params": {
            #         "country": "China"
            #     },
            # },
            #             {
            #     "name": "Get HRW Report for Chile (usually only 2024)",
            #     "params": {
            #         "country": "Chile"
            #     },
            # },
        ]

        # # Test user agent generation
        # log("\nTesting User Agent Generation:", "info")
        # for _ in range(3):  # Generate 3 random user agents
        #     headers = get_request_headers()
        #     logger.debug(f"Full headers: {headers}")

        # Use the standardized test framework
        await standardized_tool_test(
            tool_function=get_human_rights_research_by_country,
            test_scenarios=hrw_test_scenarios,
            test_title="HRW Report Retrieval Tool Test"
        )


        log("ALL TESTS COMPLETED", "success")
    
    # Run the async test function
    asyncio.run(run_tests()) 