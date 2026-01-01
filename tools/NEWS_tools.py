from typing import List, Dict, Any, Union, Optional, Literal, Tuple
from typing_extensions import TypedDict
from langchain_core.tools import tool, BaseTool
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
import logging
import os
import coloredlogs
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, quote, urlunparse
import pprint
import json
from datetime import datetime
from fake_useragent import UserAgent
import random
import time
import traceback
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import glob
from pydantic import BaseModel, Field
import asyncio
import groq
import instructor

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
    "BRAVE_SEARCH_NEWS_API_BASE_URL": "https://api.search.brave.com/res/v1/news/search",
    "BRAVE_SEARCH_API_KEY": os.getenv("BRAVE_SEARCH_API_KEY", ""),
    "PAGE_CONTENT_WORDS_LIMIT": 4000,
    # Use dedicated news key if available, otherwise fall back to main Groq key
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY_NEWS", os.getenv("GROQ_API_KEY", "")),
}

def set_api_keys(groq_api_key: str = None, brave_api_key: str = None):
    """
    Set API keys dynamically from the pipeline's Valves system.
    This allows the pipeline to pass API keys configured in OpenWebUI without hardcoding them.
    
    Args:
        groq_api_key: API key for Groq (can be dedicated news key or main key)
        brave_api_key: API key for Brave Search
    """
    global COMMON_HEADERS
    
    if groq_api_key:
        tool_specific_values["GROQ_API_KEY"] = groq_api_key
    if brave_api_key:
        tool_specific_values["BRAVE_SEARCH_API_KEY"] = brave_api_key
        # IMPORTANT: Update COMMON_HEADERS with the new API key
        COMMON_HEADERS = [
            {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": brave_api_key
            }
        ]

# Global logging control flag
LOGGING_ENABLED = False

# Initialize fake user agent
ua = UserAgent()

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


class ArticleSummary(BaseModel):
    """Model for a single article summary"""
    title: str = Field(..., description="The title of the article")
    date: str = Field(..., description="The publication date of the article")
    content: str = Field(..., description="The content/summary of the article, including all key relevant details, figures, and quotes")
    original_content: str = Field(default="", description="The original, unmodified content of the article (for citations)")
    url: str = Field(default="", description="The URL of the article")
    source: str = Field(default="", description="The source of the article (e.g., hostname)")

# Custom function to format tool results with articles array instead of content string
def format_articles_tool_result(
    articles: List[ArticleSummary],
    citations: List[Citation],
    tool_name: str,
    tool_params: Dict[str, Any],
    beacon_tool_source: str
) -> RULAC_TOOL_RESULT:
    """
    Creates a standardized tool result with articles array instead of content string.
    
    Args:
        articles: List of ArticleSummary objects
        citations: List of Citation objects
        tool_name: Name of the tool
        tool_params: Parameters used for the tool
        beacon_tool_source: Source of the data (e.g., "BBC")
        
    Returns:
        RULAC_TOOL_RESULT with articles array
    """
    # Create a content summary for backward compatibility
    content_summary = ""
    if articles:
        content_summary = f"Retrieved {len(articles)} articles from {beacon_tool_source}."
    else:
        content_summary = f"No relevant articles found from {beacon_tool_source}."
    
    return {
        "content": content_summary,  # Keep for backward compatibility
        "articles": articles,  # New field for structured article data
        "citations": citations,
        "tool_name": tool_name,
        "tool_params": tool_params,
        "beacon_tool_source": beacon_tool_source
    }

class NewsSourceResponse(BaseModel):
    """Model for the response from a news source"""
    source_name: str = Field(..., description="The name of the news source (e.g., BBC, Al Jazeera)")
    articles: List[ArticleSummary] = Field(..., description="List of article summaries")
    total_articles: int = Field(..., description="Total number of articles found")
    citations: List[Citation] = Field(..., description="List of citations")

# Function to clean Reuters snippets specifically
def clean_reuters_snippet(text):
    """Clean Reuters snippets by removing location/date prefixes and trailing (Reuters)"""
    if not text:
        return ""
    
    # Remove location and date pattern at the beginning (e.g., "CITY, Month Day (Reuters) - ")
    text = re.sub(r'^\s*[A-Z]+[A-Z\s,]+\d+\s*\(Reuters\)\s*-\s*', '', text)
    
    # Remove trailing "(Reuters)" at the end
    text = re.sub(r'\s*\(Reuters\)\s*$', '', text)
    
    # Remove any other instances of "(Reuters)" in the text with a space after
    text = re.sub(r'\(Reuters\)\s+', '', text)
    
    return text.strip()

def convert_to_human_readable_date(date_str: str) -> str:
    """
    Convert various date formats to a human-readable format (Month Day Year).
    
    Args:
        date_str: Date string in various possible formats
        
    Returns:
        Human-readable date string or the original if conversion fails
    """
    if not date_str:
        return ""
    
    try:
        # Try various date formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S", # ISO format: 2025-03-13T21:52:33
            "%Y-%m-%d %H:%M:%S",  # Standard datetime: 2025-03-13 21:52:33
            "%Y-%m-%d",           # Simple date: 2025-03-13
            "%d %b %Y",           # 13 Mar 2025
            "%B %d, %Y",          # March 13, 2025
            "%b %d, %Y"           # Mar 13, 2025
        ]:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%B %d, %Y")  # Format as "March 13, 2025"
            except ValueError:
                continue
        
        # If none of the formats match, return the original
        return date_str
    except Exception:
        # If any error occurs, return the original
        return date_str

def create_citation_for_article(article: ArticleSummary) -> Citation:
    """
    Creates a standardized citation for a news article.
    
    Args:
        article: ArticleSummary object containing article details
        
    Returns:
        Citation object for the article
    """
    # Convert date to human-readable format
    human_readable_date = convert_to_human_readable_date(article.date)
    
    # Create citation content with consistent formatting
    citation_content = f"{article.title}\n"
    citation_content += f"Source: {article.source}\n"
    citation_content += f"Published: {human_readable_date}\n\n"
    
    # Use original content for BBC, AP, and Al Jazeera; use regular content for Reuters
    if article.source in ["BBC", "AP", "Al Jazeera"] and article.original_content:
        citation_content += f"{article.original_content}\n"
    else:
        citation_content += f"{article.content}\n"
    
    # Create and return standard citation
    return create_standard_citation(
        title=article.title,
        url=article.url,
        formatted_content=citation_content
    )

# Common headers that we'll rotate through
COMMON_HEADERS = [
    {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": tool_specific_values["BRAVE_SEARCH_API_KEY"]
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


# Define log styles for rich console output
LOG_STYLES = {
    "info": {"style": "black on yellow", "border_style": "yellow"},
    "success": {"style": "black on green", "border_style": "green"},
    "error": {"style": "white on red", "border_style": "red"},
    "title": {"style": "bold white on green", "border_style": "green"}
}

def log(message, level="info", as_panel=True):
    """
    Log a message to the standard logger and conditionally print to the console.
    Console output occurs only if the logger level is DEBUG or the message level is 'error'.
    All logging can be disabled by setting LOGGING_ENABLED to False.

    Args:
        message: The message to log
        level: The log level (debug, info, success, error, title)
        as_panel: Whether to format console output as a panel
    """
    # Check if logging is enabled
    if not LOGGING_ENABLED:
        return

    # Map custom levels to standard logging methods and levels
    log_actions = {
        "debug": (logger.debug, logging.DEBUG),
        "info": (logger.info, logging.INFO),
        "success": (logger.info, logging.INFO), # Treat success as info for logging
        "error": (logger.error, logging.ERROR),
        "title": (logger.info, logging.INFO)   # Treat title as info for logging
    }

    log_method, std_level = log_actions.get(level, (logger.info, logging.INFO))

    # 1. Log to standard logger (respects logger's level)
    # Ensure message is suitable for logging (e.g., convert complex objects to string)
    log_message = str(message)
    log_method(log_message)

    # 2. Conditionally print to console using rich
    # Print if the logger level is DEBUG OR if the message level is 'error'
    should_print_to_console = logger.isEnabledFor(logging.DEBUG) or level == "error"

    if should_print_to_console:
        style_config = LOG_STYLES.get(level, LOG_STYLES["info"])
        # Ensure message is printable for the console as well
        printable_message = str(message)
        try:
            if as_panel:
                console.print(Panel(printable_message, **style_config))
            else:
                console.print(printable_message, style=style_config["style"])
        except Exception as print_error:
            # Fallback if rich printing fails for some reason
            logger.error(f"Error printing log message to console: {print_error}")
            print(f"[{level.upper()}] {printable_message}")

# Common function for article content scraping
async def generic_article_scraper(
    urls: List[str], 
    source_name: str,
    find_article_content: callable,
    clean_content: callable
) -> List[str]:
    """
    Generic function for scraping article content that can be configured for different news sources.
    
    Args:
        urls: List of URLs to scrape
        source_name: Name of the news source for logging
        find_article_content: Function that takes soup and returns the article content element
        clean_content: Function that takes article_content and returns cleaned text
        
    Returns:
        List of article text contents
    """
    # Create temp directory if it doesn't exist
    temp_dir = "temp_test_data"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Initialize results
    article_texts = []
    
    # Process each URL
    for url in urls:
        try:
            logger.debug(f"Scraping {source_name} URL: {url}")
                
            # Generate headers for this request
            headers = get_request_headers()
            logger.debug(f"Request headers: {headers}")
                
            # Fetch the page content with detailed logging
            logger.debug(f"Making HTTP request to: {url}")
            response = requests.get(url, headers=headers, timeout=120)
            
            # Log response details
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Check for redirects
            if response.history:
                logger.debug(f"Request was redirected {len(response.history)} times")
                for r in response.history:
                    logger.debug(f"Redirect: {r.status_code} - {r.url}")
                logger.debug(f"Final URL: {response.url}")
            
            # Check for common issues
            if response.status_code == 403:
                logger.warning(f"Access Forbidden (403) - Site may be blocking scrapers")
            elif response.status_code == 404:
                logger.warning(f"Page Not Found (404) - The article may have been removed")
            elif response.status_code == 302 or response.status_code == 301:
                logger.warning(f"Redirect detected - Final URL: {response.url}")
            
            # Raise for other bad status codes
            response.raise_for_status()
            
            # Log response content type and size
            content_type = response.headers.get('Content-Type', 'unknown')
            logger.debug(f"Response Content-Type: {content_type}")
            logger.debug(f"Response size: {len(response.text)} characters")
            
            # Save a sample of the HTML for debugging
            html_sample = response.text[:500] + "..." if len(response.text) > 500 else response.text
            logger.debug(f"HTML sample: {html_sample}")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # # Check if we're hitting a paywall or login page
            # paywall_indicators = ['paywall', 'subscribe', 'subscription', 'sign in', 'login', 'premium']
            # for indicator in paywall_indicators:
            #     if indicator in response.text.lower():
            #         logger.warning(f"Possible paywall/subscription content detected: '{indicator}'")
            
            # Debug HTML structure
            title_tag = soup.find('title')
            logger.debug(f"Page title: {title_tag.text if title_tag else 'No title found'}")
            
            # Find the main article content using the provided function
            logger.debug(f"Looking for main content container using find_{source_name.lower().replace(' ', '_')}_content()")
            article_content = find_article_content(soup)
            
            # Process the content if article was found
            if article_content:
                logger.debug(f"Found main content container, type: {type(article_content)}, tag: {article_content.name}")
                # Use the provided cleaning function
                text = clean_content(article_content)
                
                # Log text statistics
                logger.debug(f"Text length before truncation: {len(text.split())} words")
                
                # Limit to specified number of words
                words = text.split()
                if len(words) > tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"]:
                    text = " ".join(words[:tool_specific_values["PAGE_CONTENT_WORDS_LIMIT"]])
                    logger.debug(f"Truncated content to {tool_specific_values['PAGE_CONTENT_WORDS_LIMIT']} words")
            else:
                text = ""
                logger.warning(f"Could not find main content container for {source_name}")
            
            # Add the text content to the results
            article_texts.append(text)
            
            logger.debug(f"Successfully scraped: {url}")
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Add empty content for failed scrapes
            article_texts.append("")
    
    return article_texts

# BBC News content finder
def find_bbc_content(soup):
    # Log the URL if available in the soup
    url = ""
    if soup.find('meta', property='og:url'):
        url = soup.find('meta', property='og:url').get('content', '')
        logger.debug(f"Processing BBC page with URL: {url}")
    
    # Try to find article tag
    article = soup.find('article')
    if article:
        logger.debug(f"Found main article container with tag 'article'")
        return article
    
    # If no article tag, try alternative selectors common in BBC pages
    logger.debug(f"No 'article' tag found, trying alternative selectors")
    
    # Try main content container with specific classes
    alt_selectors = [
        ('div', {'class': 'story-body'}),
        ('div', {'class': 'story-body__inner'}), 
        ('div', {'data-component': 'text-block'}),
        ('div', {'class': 'body-content'}),
        ('main', {}),
        ('div', {'role': 'main'}),
        ('div', {'class': 'ssrcss-1ocoo3l-Wrap'})  # Modern BBC layout wrapper
    ]
    
    for tag, attrs in alt_selectors:
        content = soup.find(tag, attrs)
        if content:
            logger.debug(f"Found alternative content container with tag '{tag}' and attributes {attrs}")
            return content
            
    # If still not found, log HTML structure overview to help debug
    logger.debug("Could not find any suitable content container, logging page structure")
    
    # Log available meta tags for context
    logger.debug("Available meta tags:")
    for meta in soup.find_all('meta')[:10]:  # Limit to first 10 to avoid overwhelming logs
        logger.debug(f"  {meta}")
        
    # Log main body structure to help debug
    body = soup.find('body')
    if body:
        # Get direct children of body for structural overview
        logger.debug("Body structure (first level children):")
        for i, child in enumerate(list(body.children)[:10]):  # Limit to first 10
            if hasattr(child, 'name') and child.name:
                class_attr = child.get('class', [])
                id_attr = child.get('id', '')
                logger.debug(f"  Child {i}: <{child.name}> class='{class_attr}' id='{id_attr}'")
    
    logger.warning("Could not find BBC article content in any known container")
    return None

# BBC News content cleaner
def clean_bbc_content(article_content):
    # Add basic check if article_content is None
    if article_content is None:
        logger.warning("Cannot clean BBC content: article_content is None")
        return ""
        
    # Rest of the function remains the same
    # Remove all script and style elements
    for element in article_content.find_all(['script', 'style']):
        element.decompose()
    
    # Remove all navigation elements
    for nav in article_content.find_all('nav'):
        nav.decompose()
    
    # Remove all button elements (often used for sharing, etc)
    for button in article_content.find_all('button'):
        button.decompose()
    
    # Remove all ul elements (typically contains related links)
    for element in article_content.find_all('ul'):
        element.decompose()
    
    # Remove links blocks and other components
    for element in article_content.find_all(attrs={
        "data-component": [
            "topic-list",
            "tag-list",
            "share-tools",
            "recommendations",
            "related-content",
            "links-block"
        ]
    }):
        element.decompose()
    
    # Remove specific BBC elements that contain related content
    for element in article_content.find_all(class_=['topic-list', 'article__topics', 'article-share', 'article-footer']):
        element.decompose()
    
    # Process paragraphs and headers to preserve structure
    paragraphs = []
    
    # Find all text-containing elements, focusing on actual article content
    for element in article_content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6']):
        # Skip elements that are part of navigation, sharing, or related content
        if element.find_parent(attrs={"data-component": ["links-block", "topic-list", "tag-list", "share-tools", 
                                                       "recommendations", "related-content"]}):
            continue
            
        # Process all text nodes and links within the element
        text_parts = []
        for content in element.contents:
            if isinstance(content, str):  # Text node
                text_parts.append(content.strip())
            elif content.name == 'a':  # Link
                # Skip links that are likely to be related content
                if not content.find_parent(attrs={"data-component": ["links-block", "topic-list", "tag-list"]}):
                    text_parts.append(content.get_text(strip=True))
            elif content.name in ['em', 'i', 'strong', 'b', 'span']:  # Inline formatting
                text_parts.append(content.get_text(strip=True))
        
        # Join all parts and normalize spaces
        text = ' '.join(text_parts)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:  # Only add non-empty paragraphs
            paragraphs.append(text)
    
    # Join paragraphs with double newlines to preserve structure
    text = '\n\n'.join(paragraphs)
    
    # Clean up the text
    text = re.sub(r'[ \t]+', ' ', text)  # Clean up spaces and tabs, preserve newlines
    text = re.sub(r'\s+([,\.])', r'\1', text)  # Remove spaces before punctuation
    text = text.strip()
    
    return text

# Al Jazeera content finder
def find_aljazeera_content(soup):
    return soup.find('div', class_='wysiwyg wysiwyg--all-content')

# Al Jazeera content cleaner
def clean_aljazeera_content(article_content):
    # First, remove all unwanted elements
    elements_to_remove = [
        # Remove recommended stories
        {'class_': 'more-on'},
        # Remove all ad containers
        {'class_': 'container--ads'},
        # Remove newsletter signup
        {'class_': 'article-newsletter-slot'},
        # Remove screen reader text
        {'class_': 'screen-reader-text'}
    ]
    
    for criteria in elements_to_remove:
        for element in article_content.find_all(class_=criteria['class_']):
            element.decompose()
    
    # Process content in order to maintain structure
    content_elements = []
    
    # Helper function to process text from an element
    def process_element_text(element):
        text_parts = []
        for content in element.contents:
            if isinstance(content, str):
                text_parts.append(content.strip())
            elif content.name == 'a':
                text_parts.append(content.get_text(strip=True))
            elif content.name in ['em', 'i', 'strong', 'b', 'span', 'p']:
                text_parts.append(content.get_text(strip=True))
        
        # Join and clean the text
        text = ' '.join(text_parts)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # First, handle headings and paragraphs at the top level
    for element in article_content.children:
        # Skip if not a tag
        if not hasattr(element, 'name'):
            continue
        
        # Process based on element type
        if element.name in ['p', 'h2', 'h3']:
            text = process_element_text(element)
            
            # Add heading marker for h2/h3
            if element.name == 'h2':
                text = f"\n## {text}\n"
            elif element.name == 'h3':
                text = f"\n### {text}\n"
                
            if text:  # Only add non-empty elements
                content_elements.append(text)
        
        # Handle lists at the top level
        elif element.name == 'ul':
            # Process each list item
            for li in element.find_all('li', recursive=False):
                list_text = "- " + process_element_text(li)
                if list_text:  # Only add non-empty elements
                    content_elements.append(list_text)
    
    # Now also find all lists in the article (for nested lists)
    for ul in article_content.find_all('ul'):
        # Check if we already processed this list at the top level
        if ul.parent == article_content:
            continue  # Skip already processed lists
            
        # Process each list item in this nested list
        for li in ul.find_all('li', recursive=False):
            list_text = "- " + process_element_text(li)
            if list_text:  # Only add non-empty elements
                content_elements.append(list_text)
    
    # Join all elements with appropriate spacing
    text = '\n'.join(content_elements)
    
    # Clean up the text
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace multiple newlines with double newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Clean up spaces and tabs
    text = re.sub(r'\s+([,\.])', r'\1', text)  # Remove spaces before punctuation
    text = text.strip()
    
    return text

# AP News content finder
def find_ap_content(soup):
    # Look for the main article content - AP News typically uses RichTextStoryBody
    article_content = soup.find('div', class_='RichTextStoryBody RichTextBody')
    
    # If RichTextStoryBody isn't found, try the Article class as fallback
    if not article_content:
        article_content = soup.find('div', class_='Article')
    
    # Last resort - try to find any main content container
    if not article_content:
        article_content = soup.find('main') or soup.find('article')
        
    return article_content

# AP News content cleaner
def clean_ap_content(article_content):
    # For the fallback case where we found main/article
    if article_content.name in ['main', 'article'] and not article_content.find(class_='RichTextStoryBody'):
        paragraphs = []
        for element in article_content.find_all(['p', 'h2', 'h3', 'h4']):
            if element.name.startswith('h'):
                paragraphs.append(f"\n## {element.get_text(strip=True)}\n")
            else:
                paragraphs.append(element.get_text(strip=True))
        
        text = '\n\n'.join(paragraphs)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # Regular AP article
    # Remove unwanted elements
    elements_to_remove = [
        # Remove ad containers
        {'class_': 'ad-placeholder'},
        {'class_': 'SovrnAd'},
        {'class_': 'Advertisement'},
        # Remove related content
        {'class_': 'Related'},
        {'class_': 'PageListEnhancementGeneric'},
        {'class_': 'HTMLModuleEnhancement'},
        # Remove social media sharing
        {'class_': 'social-share'},
        # Remove newsletter signup
        {'class_': 'newsletter-subscribe'},
        # Remove media components that are not part of the main article
        {'class_': 'Media-caption'}
    ]
    
    for criteria in elements_to_remove:
        for attribute, value in criteria.items():
            for element in article_content.find_all(class_=value):
                element.decompose()
    
    # Process article content to extract text
    paragraphs = []
    
    # Process headings first
    for heading in article_content.find_all(['h1', 'h2', 'h3', 'h4']):
        heading_text = heading.get_text(strip=True)
        if heading_text:
            paragraphs.append(f"\n## {heading_text}\n")
    
    # Then process paragraphs
    for para in article_content.find_all('p'):
        # Skip paragraphs within unwanted elements that weren't caught earlier
        if para.find_parent(class_=['SovrnAd', 'Advertisement', 'Related', 'social-share', 'newsletter-subscribe']):
            continue
        
        # Process text within the paragraph
        text_parts = []
        for content in para.contents:
            if isinstance(content, str):  # Text node
                text_parts.append(content.strip())
            elif content.name == 'a':  # Link
                text_parts.append(content.get_text(strip=True))
            elif content.name in ['em', 'i', 'strong', 'b', 'span']:  # Inline formatting
                text_parts.append(content.get_text(strip=True))
        
        # Join and clean text
        text = ' '.join(text_parts)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:  # Only add non-empty paragraphs
            paragraphs.append(text)
    
    # Join paragraphs with double newlines to preserve structure
    text = '\n\n'.join(paragraphs)
    
    # Clean up the text
    text = re.sub(r'[ \t]+', ' ', text)  # Clean up spaces and tabs
    text = re.sub(r'\s+([,\.])', r'\1', text)  # Remove spaces before punctuation
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace multiple newlines with double newlines
    text = text.strip()
    
    return text

# Replace the original scraping functions with versions that use the generic scraper
async def async_scrape_BBC_news(urls: List[str]) -> List[str]:
    """
    Asynchronously scrape multiple BBC URLs using the generic scraper.
    
    Args:
        urls: List of URLs to scrape
        
    Returns:
        List of article text content
    """
    return await generic_article_scraper(
        urls=urls,
        source_name="BBC",
        find_article_content=find_bbc_content,
        clean_content=clean_bbc_content
    )

async def async_scrape_AlJazeera_news(urls: List[str]) -> List[str]:
    """
    Asynchronously scrape multiple Al Jazeera URLs using the generic scraper.
    
    Args:
        urls: List of URLs to scrape
        
    Returns:
        List of article text content
    """
    return await generic_article_scraper(
        urls=urls,
        source_name="Al Jazeera",
        find_article_content=find_aljazeera_content,
        clean_content=clean_aljazeera_content
    )

async def async_scrape_AP_news(urls: List[str]) -> List[str]:
    """
    Asynchronously scrape multiple Associated Press (AP) URLs using the generic scraper.
    
    Args:
        urls: List of URLs to scrape
        
    Returns:
        List of article text content
    """
    return await generic_article_scraper(
        urls=urls,
        source_name="AP News",
        find_article_content=find_ap_content,
        clean_content=clean_ap_content
    )

async def get_search_results(query: str, number_of_results: int = 1, search_type: Literal["web", "news"] = "web") -> List[Dict[str, Any]]:
    """
    Get search results from the Brave Search API.
    
    Args:
        query: The search query string
        number_of_results: Maximum number of results to return
        search_type: Type of search to perform ("web" or "news")
        
    Returns:
        List of search result dictionaries
    """
    try:
        # if logger is enabled for debug, then log the search query
        if logger.isEnabledFor(logging.DEBUG):
            log(f"Connecting to Brave Search API for {search_type} search with query: {query}")
        
        # Set up query parameters
        params = {
            "q": query,
            "count": number_of_results,
            "search_lang": "en",
            "ui_lang": "en-US",
            "safesearch": "off",
            "text_decorations": "1",
            "spellcheck": "1",
        }
        
        # Set result filter based on search type
        if search_type == "web":
            params["result_filter"] = "web"
        elif search_type == "news":
            params["result_filter"] = "news"
        
        # Select appropriate API endpoint based on search type
        api_url = (tool_specific_values["BRAVE_SEARCH_NEWS_API_BASE_URL"] 
                  if search_type == "news" 
                  else tool_specific_values["BRAVE_SEARCH_API_BASE_URL"])
        
        logger.debug(f"Using API endpoint: {api_url}")
        logger.debug(f"Search parameters: {json.dumps(params, indent=2)}")
        
        # Generate headers for this request
        headers = get_request_headers()
        logger.debug(f"Request headers: {json.dumps(headers, indent=2)}")
        
        # Send the request to the Brave Search API
        resp = requests.get(
            api_url,
            params=params,
            headers=headers,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Log the full response for debugging
        # log(f"Full API Response for {search_type} search:", "info")
        # log(json.dumps(data, indent=2), "info", False)

        # Helper function to clean HTML content
        def clean_html_content(text):
            """Clean HTML tags and entities from text"""
            if not text:
                return ""
                
            # First remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Use HTML parser to handle all entities comprehensively
            import html
            text = html.unescape(text)
            
            return text

        # Extract results from Brave Search response
        results = []
        
        # Process results based on search type
        if search_type == "news":
            if "results" in data:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Found {len(data['results'])} news results")
                for result in data["results"]:
                    # Clean the description by removing HTML tags and entities
                    full_cleaned_content = clean_html_content(result.get("description", ""))
                    
                    results.append({
                        "title": result.get("title", ""),
                        "link": result.get("url", ""),
                        "snippet": full_cleaned_content,
                        "category": "news",
                        "publication_date": result.get("page_age", ""),  # News API uses page_age
                        "source": result.get("meta_url", {}).get("hostname", ""),
                    })
        else:  # web search
            if "web" in data and "results" in data["web"]:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Found {len(data['web']['results'])} web results")
                for result in data["web"]["results"]:
                    # Clean description from HTML tags and entities
                    cleaned_description = clean_html_content(result.get("description", ""))
                    
                    results.append({
                        "title": result.get("title", ""),
                        "link": result.get("url", ""),
                        "snippet": cleaned_description,
                        "category": "web",
                        "publication_date": result.get("page_age", "")
                    })
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Total results after processing: {len(results)}")
        # specify the search type in the log message
        log(f"Found {len(results)} {search_type} search results", "success")
        return results
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Search engine error for {search_type} search: {str(e)}"
        log(error_msg, "error")
        logger.error(f"Full error details: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []



def clean_article_title(title: str) -> str:
    """
    Cleans article titles by removing the pipe character '|' and anything after it.
    
    Args:
        title: The original title string
        
    Returns:
        Cleaned title string
    """
    if '|' in title:
        # Return everything before the first pipe character
        return title.split('|')[0].strip()
    return title

async def get_latest_news_from_Reuters_source(
    search_query: str, 
    source_url: str,
    web_results_count: int,
    news_results_count: int
) -> NewsSourceResponse:
    """
    Specialized function for retrieving Reuters news articles that uses snippets instead of scraping.
    
    Args:
        search_query: The search query to find relevant news articles
        source_url: The base URL for the news source (e.g., "www.reuters.com/world")
        web_results_count: Number of web search results to fetch
        news_results_count: Number of news search results to fetch
        
    Returns:
        A standardized NewsSourceResponse
    """
    tool_name = "get_latest_news_from_Reuters"
    
    # Print start marker for tool execution, if debug
    if logger.isEnabledFor(logging.DEBUG):  
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     f"STARTING TOOL: {tool_name}\n" + 
                     "="*50 + "[/bold white]\n")
    
    # Set up tool metadata for result
    research_task = f"Retrieve Reuters news articles about '{search_query}'"
    tool_params = {
        "search_query": search_query,
        "research_task": research_task
    }
    
    try:
        # Construct the search query with site filter
        initial_search_query = search_query
        search_query = f'site:{source_url} {search_query}'
        log(f"Searching Reuters news: \"{search_query}\"", "debug")
        
        # Initialize results containers
        web_search_results = []
        news_search_results = []
        
        # Get web search results if count > 0
        if web_results_count > 0:
            web_search_results = await get_search_results(
                query=search_query,
                number_of_results=web_results_count,
                search_type="web"
            )
        else:
            log("Skipping web search as web_results_count is 0", "debug")
        
        # Get news search results if count > 0
        if news_results_count > 0:
            news_search_results = await get_search_results(
                query=search_query,
                number_of_results=news_results_count,
                search_type="news"
            )
        else:
            log("Skipping news search as news_results_count is 0", "debug")
        
        # Remove duplicates based on URL before combining results
        seen_urls = set()
        deduplicated_results = []
        
        # Helper function to add unique results
        def add_unique_results(results):
            for result in results:
                url = result.get('link')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    # Clean the title by removing the pipe character and anything after it
                    if 'title' in result:
                        result['title'] = clean_article_title(result['title'])
                    deduplicated_results.append(result)
        
        # Add web results first (they tend to be more comprehensive)
        add_unique_results(web_search_results)
        # Then add news results
        add_unique_results(news_search_results)
        
        # Sort results by publication date in ascending order (oldest first)
        deduplicated_results.sort(key=lambda x: x.get("publication_date", ""))
        
        # Use deduplicated results instead of raw combination
        search_results = deduplicated_results
        
        # # Pretty print the results for debugging (only in DEBUG mode)
        # if logger.isEnabledFor(logging.DEBUG):
        #     log("Search Results:", "debug")
        #     log(f"Found {len(web_search_results)} web results and {len(news_search_results)} news results", "debug")
        #     for i, result in enumerate(search_results, 1):
        #         log(f"\nResult {i}:", "debug")
        #         log(f"Title: {result.get('title', 'No title')}", "debug")
        #         log(f"Link: {result.get('link', 'No link')}", "debug")
        #         log(f"Snippet: {result.get('snippet', 'No snippet')}", "debug")
        #         log(f"Category: {result.get('category', 'No category')}", "debug")
        #         log(f"Source: {result.get('source', 'No source')}", "debug")
        #         log(f"Publication Date: {result.get('publication_date', 'No date')}", "debug")
        #         log("-" * 50, "debug")
        
        # Initialize containers for results
        article_summaries = []
        citations = []
        
        if search_results:
            if logger.isEnabledFor(logging.DEBUG):
                log(f"Processing {len(search_results)} search results")
            
            # Use snippets from search results directly without AI summarization
            for i, result in enumerate(search_results):
                url = result.get("link", "")
                title = result.get("title", f"Reuters news article about {initial_search_query}")
                publication_date = result.get("publication_date", "")
                content = result.get("snippet", "")
                
                if not content:
                    continue
                
                # Apply Reuters-specific cleaning
                content = clean_reuters_snippet(content)
                
                # Create ArticleSummary directly from the snippet without summarization
                # For Reuters, we use the same snippet content for both content and original_content
                article_summary = ArticleSummary(
                    title=title,
                    date=publication_date,
                    content=content,
                    original_content=content,  # For Reuters, the snippet is the content we want in citations
                    url=url,
                    source="Reuters"
                )
                article_summaries.append(article_summary)
                
                # Create citation
                citation = create_citation_for_article(article_summary)
                
                citations.append(citation)
                
                logger.debug(f"Created citation for article: '{title[:50]}...'")
            
            log(f"Created {len(article_summaries)} articles directly from snippets", "debug")
        else:
            log("No search results found", "error")
        
        log(f"Successfully retrieved {len(article_summaries)} relevant snippets", "debug")
        
        # Print end marker for tool execution, if debug
        if logger.isEnabledFor(logging.DEBUG):
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (success)\n" + 
                         "="*50 + "[/bold white]\n")
        
        # Return structured response
        return NewsSourceResponse(
            source_name="Reuters",
            articles=article_summaries,
            total_articles=len(article_summaries),
            citations=citations
        )
    
    except Exception as e:
        error_message = f"Error retrieving Reuters News articles: {str(e)}"
        log(error_message, "error")
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return error response
        return NewsSourceResponse(
            source_name="Reuters",
            articles=[],
            total_articles=0,
            citations=[]
        )

async def get_latest_news_from_source(
    search_query: str, 
    source_name: str, 
    source_url: str,
    web_results_count: int,
    news_results_count: int,
    scrape_function: callable
) -> NewsSourceResponse:
    """
    Helper function that retrieves the latest news articles from a specified news source.
    
    Args:
        search_query: The search query to find relevant news articles
        source_name: The name of the news source (e.g., "BBC", "Al Jazeera")
        source_url: The base URL for the news source (e.g., "www.bbc.com/news")
        web_results_count: Number of web search results to fetch (0 to skip web search)
        news_results_count: Number of news search results to fetch (0 to skip news search)
        scrape_function: The specific scraping function to use for this source
        
    Returns:
        A standardized NewsSourceResponse
    """
    tool_name = f"get_latest_news_from_{source_name.replace(' ', '')}"
    
    # Print start marker for tool execution, if debug
    if logger.isEnabledFor(logging.DEBUG):
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     f"STARTING TOOL: {tool_name}\n" + 
                     "="*50 + "[/bold white]\n")
    
    # Set up tool metadata for result
    research_task = f"Retrieve {source_name} news articles about '{search_query}'"
    tool_params = {
        "search_query": search_query,
        "research_task": research_task
    }
    
    try:
        # Construct the search query with site filter
        initial_search_query = search_query
        search_query = f'site:{source_url} {search_query}'
        logger.debug(f"Searching {source_name} news: \"{search_query}\"")
        
        # Initialize results containers
        web_search_results = []
        news_search_results = []
        
        # Get web search results if count > 0
        if web_results_count > 0:
            web_search_results = await get_search_results(
                query=search_query,
                number_of_results=web_results_count,
                search_type="web"
            )
        else:
            log("Skipping web search as web_results_count is 0", "debug")
        
        # Get news search results if count > 0
        if news_results_count > 0:
            news_search_results = await get_search_results(
                query=search_query,
                number_of_results=news_results_count,
                search_type="news"
            )
        else:
            log("Skipping news search as news_results_count is 0", "debug")
        
        # Remove duplicates based on URL before combining results
        seen_urls = set()
        deduplicated_results = []
        
        # Helper function to add unique results
        def add_unique_results(results):
            for result in results:
                url = result.get('link')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    # Clean the title by removing the pipe character and anything after it
                    if 'title' in result:
                        result['title'] = clean_article_title(result['title'])
                    # Ensure source is set to the news source name
                    result['source'] = source_name
                    deduplicated_results.append(result)
        
        # Add web results first (they tend to be more comprehensive)
        add_unique_results(web_search_results)
        # Then add news results
        add_unique_results(news_search_results)
        
        # Sort results by publication date in ascending order (oldest first)
        deduplicated_results.sort(key=lambda x: x.get("publication_date", ""))
        
        # Use deduplicated results instead of raw combination
        search_results = deduplicated_results
        
        # Initialize containers for results
        article_summaries = []
        citations = []
        
        if search_results:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processing {len(search_results)} search results")
            
            # Initialize Groq LLM for article summarization
            groq_api_key = tool_specific_values["GROQ_API_KEY"]
            chat = ChatGroq(
                groq_api_key=groq_api_key,
                model="llama-3.1-8b-instant",
                temperature=0,
            )
            
            # Get URLs from results
            urls = [r["link"] for r in search_results]
            
            try:
                logger.debug(f"Scraping content from {len(urls)} pages...")
                article_texts = await scrape_function(urls)
                
                # Store original article contents in a dictionary for citation purposes
                # original_contents = {url: text for url, text in zip(urls, article_texts) if text}
                
                # Process and summarize each article in parallel
                summarization_tasks = []
                
                # Prepare all summarization tasks
                for i, (url, title, publication_date, article_text) in enumerate(zip(
                    urls, 
                    [r["title"] for r in search_results], 
                    [r["publication_date"] for r in search_results], 
                    article_texts
                )):
                    if not article_text:
                        continue
                    
                    # Create task for summarizing this article
                    summarization_tasks.append({
                        "index": i,
                        "url": url,
                        "title": title,
                        "publication_date": publication_date,
                        "content": article_text,
                        "task": summarize_individual_article(
                            chat=chat,
                            title=title,
                            date=publication_date,
                            content=article_text,
                            source_name=source_name,
                            url=url
                        )
                    })
                
                # Run summarization tasks in parallel
                if summarization_tasks:
                    log(f"Summarizing {len(summarization_tasks)} articles in parallel...", "debug")
                    summary_start_time = time.time()
                    
                    # Execute all tasks in parallel (up to 3 at a time to avoid overloading the API)
                    # Create batches of 3 tasks
                    batch_size = 3
                    for i in range(0, len(summarization_tasks), batch_size):
                        batch = summarization_tasks[i:i+batch_size]
                        log(f"Processing batch {i//batch_size + 1}/{(len(summarization_tasks)-1)//batch_size + 1}...", "debug")
                        
                        # Execute this batch in parallel
                        batch_results = await asyncio.gather(
                            *[task["task"] for task in batch],
                            return_exceptions=True
                        )
                        
                        # Process the batch results
                        for task, result in zip(batch, batch_results):
                            # Check if the result is an exception
                            if isinstance(result, Exception):
                                log(f"Error summarizing article {task['index']+1}: {str(result)}", "error")
                                continue
                            
                            # Add the summary to our collection if valid
                            if result:
                                article_summaries.append(result)
                                
                                # Create citation
                                citation = create_citation_for_article(result)
                                citations.append(citation)
                                
                                logger.debug(f"Created citation for article: '{task['title'][:50]}...'")
                    
                    summary_elapsed = time.time() - summary_start_time
                    log(f"Parallel summarization completed in {summary_elapsed:.2f} seconds", "debug")
                
            except Exception as e:
                log(f"Error during page scraping: {str(e)}", "error")

        else:
            log("No search results found", "error")
        
        log(f"Successfully retrieved and summarized {len(article_summaries)} relevant articles", "debug")
        
        # Print end marker for tool execution, if debug
        if logger.isEnabledFor(logging.DEBUG):
            console.print("\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (success)\n" + 
                         "="*50 + "[/bold white]\n")
        
        # Return structured response
        return NewsSourceResponse(
            source_name=source_name,
            articles=article_summaries,
            total_articles=len(article_summaries),
            citations=citations
        )
    
    except Exception as e:
        error_message = f"Error retrieving {source_name} News articles: {str(e)}"
        log(error_message, "error")
        
        # Print end marker for tool execution
        console.print("\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return error response
        return NewsSourceResponse(
            source_name=source_name,
            articles=[],
            total_articles=0,
            citations=[]
        )

@tool
async def get_latest_news_from_Reuters(search_query: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves the latest news articles from Reuters News based on the provided search query.
    Uses article snippets instead of scraping full content due to Reuters site protections.
    
    :param search_query: The search query to find relevant Reuters news articles
    :return: A dictionary with "articles" containing an array of article summaries and "citations" list
    """
    result = await get_latest_news_from_Reuters_source(
        search_query=search_query,
        source_url="www.reuters.com/world",
        web_results_count=5,
        news_results_count=5
    )
    
    # Convert NewsSourceResponse to RULAC_TOOL_RESULT format
    if result.total_articles == 0:
        return format_articles_tool_result(
            articles=[],
            citations=[],
            tool_name="get_latest_news_from_Reuters",
            tool_params={"search_query": search_query},
            beacon_tool_source="Reuters"
        )
    
    # Format articles for display if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        for article in result.articles:
            # Create a formatted panel for the article
            article_panel = Panel(
            f"[bold]Title:[/bold] {article.title}\n"
            f"[bold]Date:[/bold] {article.date}\n"
            f"[bold]Source:[/bold] {article.source}\n"
            f"[bold]Content:[/bold]\n{article.content}",
            title="Article Details",
            border_style="blue",
            style="white on blue"
            )
            console.print(article_panel)
    
    # Create citations for articles
    citations = []
    for article in result.articles:
        # Create and add citation for this article
        citation = create_citation_for_article(article)
        citations.append(citation)
    
    # Create a formatted panel for citations if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        citations_panel = Panel(
            "\n".join([
                f"[bold]Citation {i+1}:[/bold]\n"
            f"URL: {c['url']}\n"
            f"Content: {c['formatted_content']}"
            for i, c in enumerate(citations)
        ]),
        title="Article Citations",
        border_style="green",
        style="white on green"
        )
        console.print(citations_panel)

    return format_articles_tool_result(
        articles=result.articles,
        citations=citations,
        tool_name="get_latest_news_from_Reuters",
        tool_params={"search_query": search_query},
        beacon_tool_source="Reuters"
    )

@tool
async def get_latest_news_from_BBC(search_query: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves the latest news articles from BBC News based on the provided search query.
    
    :param search_query: The search query to find relevant BBC news articles
    :return: A dictionary with "articles" containing an array of article summaries and "citations" list
    """
    result = await get_latest_news_from_source(
        search_query=search_query,
        source_name="BBC",
        source_url="www.bbc.com/news/articles",
        web_results_count=1,
        news_results_count=0,
        scrape_function=async_scrape_BBC_news
    )
    
    # Convert NewsSourceResponse to RULAC_TOOL_RESULT format
    if result.total_articles == 0:
        return format_articles_tool_result(
            articles=[],
            citations=[],
            tool_name="get_latest_news_from_BBC",
            tool_params={"search_query": search_query},
            beacon_tool_source="BBC"
        )
    
    # Format articles for display if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        for article in result.articles:
            # Create a formatted panel for the article
            article_panel = Panel(
            f"[bold]Title:[/bold] {article.title}\n"
            f"[bold]Date:[/bold] {article.date}\n"
            f"[bold]Source:[/bold] {article.source}\n"
            f"[bold]Content:[/bold]\n{article.content}",
            title="Article Details",
            border_style="blue",
            style="white on blue"
            )
            console.print(article_panel)

    # Create citations for articles
    citations = []
    for article in result.articles:
        # Convert date to human-readable format
        human_readable_date = convert_to_human_readable_date(article.date)

        # Create citation for this specific article
        citation_content = f"{article.title}\n"
        citation_content += f"Source: BBC\n"
        citation_content += f"Published: {human_readable_date}\n\n"
        citation_content += f"{article.content}\n"
        
        # Create and add citation for this article
        citation = create_citation_for_article(article)
        citations.append(citation)
    
    # Create a formatted panel for citations if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        citations_panel = Panel(
            "\n".join([
                f"[bold]Citation {i+1}:[/bold]\n"
            f"URL: {c['url']}\n"
            f"Content: {c['formatted_content']}"
            for i, c in enumerate(citations)
        ]),
        title="Article Citations",
        border_style="green",
        style="white on green"
        )
        console.print(citations_panel)
    
    return format_articles_tool_result(
        articles=result.articles,
        citations=citations,
        tool_name="get_latest_news_from_BBC",
        tool_params={"search_query": search_query},
        beacon_tool_source="BBC"
    )

@tool
async def get_latest_news_from_AlJazeera(search_query: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves the latest news articles from Al Jazeera News based on the provided search query.
    
    :param search_query: The search query to find relevant Al Jazeera news articles
    :return: A dictionary with "articles" containing an array of article summaries and "citations" list
    """
    result = await get_latest_news_from_source(
        search_query=search_query,
        source_name="Al Jazeera",
        source_url="www.aljazeera.com/news",
        web_results_count=1,
        news_results_count=0,
        scrape_function=async_scrape_AlJazeera_news
    )
    
    # Convert NewsSourceResponse to RULAC_TOOL_RESULT format
    if result.total_articles == 0:
        return format_articles_tool_result(
            articles=[],
            citations=[],
            tool_name="get_latest_news_from_AlJazeera",
            tool_params={"search_query": search_query},
            beacon_tool_source="Al Jazeera"
        )
    
    # Format articles for display if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        for article in result.articles:
            # Create a formatted panel for the article
            article_panel = Panel(
            f"[bold]Title:[/bold] {article.title}\n"
            f"[bold]Date:[/bold] {article.date}\n"
            f"[bold]Source:[/bold] {article.source}\n"
            f"[bold]Content:[/bold]\n{article.content}",
            title="Article Details",
            border_style="blue",
            style="white on blue"
            )
            console.print(article_panel)

    # Create citations for articles
    citations = []
    for article in result.articles:
        # Convert date to human-readable format
        human_readable_date = convert_to_human_readable_date(article.date)

        # Create citation for this specific article
        citation_content = f"{article.title}\n"
        citation_content += f"Source: Al Jazeera\n"
        citation_content += f"Published: {human_readable_date}\n\n"
        citation_content += f"{article.content}\n"
        
        # Create and add citation for this article
        citation = create_citation_for_article(article)
        citations.append(citation)
    
    # Create a formatted panel for citations if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        citations_panel = Panel(
            "\n".join([
                f"[bold]Citation {i+1}:[/bold]\n"
            f"URL: {c['url']}\n"
            f"Content: {c['formatted_content']}"
            for i, c in enumerate(citations)
        ]),
        title="Article Citations",
        border_style="green",
        style="white on green"
        )
        console.print(citations_panel)

    return format_articles_tool_result(
        articles=result.articles,
        citations=citations,
        tool_name="get_latest_news_from_AlJazeera",
        tool_params={"search_query": search_query},
        beacon_tool_source="Al Jazeera"
    )

@tool
async def get_latest_news_from_AP(search_query: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves the latest news articles from Associated Press (AP) News based on the provided search query.
    
    :param search_query: The search query to find relevant AP news articles
    :return: A dictionary with "articles" containing an array of article summaries and "citations" list
    """
    result = await get_latest_news_from_source(
        search_query=search_query,
        source_name="AP",
        source_url="apnews.com/article",
        web_results_count=1,
        news_results_count=0,
        scrape_function=async_scrape_AP_news
    )
    
    # Convert NewsSourceResponse to RULAC_TOOL_RESULT format
    if result.total_articles == 0:
        return format_articles_tool_result(
            articles=[],
            citations=[],
            tool_name="get_latest_news_from_AP",
            tool_params={"search_query": search_query},
            beacon_tool_source="AP"
        )
    
    # Format articles for display if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        for article in result.articles:
            # Create a formatted panel for the article
            article_panel = Panel(
            f"[bold]Title:[/bold] {article.title}\n"
            f"[bold]Date:[/bold] {article.date}\n"
            f"[bold]Source:[/bold] {article.source}\n"
            f"[bold]Content:[/bold]\n{article.content}",
            title="Article Details",
            border_style="blue",
            style="white on blue"
            )
            console.print(article_panel)
    
    # Create citations for articles
    citations = []
    for article in result.articles:
        # Convert date to human-readable format
        human_readable_date = convert_to_human_readable_date(article.date)

        # Create citation for this specific article
        citation_content = f"{article.title}\n"
        citation_content += f"Source: AP\n"
        citation_content += f"Published: {human_readable_date}\n\n"
        citation_content += f"{article.content}\n"
        
        # Create and add citation for this article
        citation = create_citation_for_article(article)
        citations.append(citation)
    
    # Create a formatted panel for citations if debug mode is enabled
    if logger.isEnabledFor(logging.DEBUG):
        citations_panel = Panel(
            "\n".join([
                f"[bold]Citation {i+1}:[/bold]\n"
            f"URL: {c['url']}\n"
            f"Content: {c['formatted_content']}"
            for i, c in enumerate(citations)
        ]),
        title="Article Citations",
        border_style="green",
        style="white on green"
        )
        console.print(citations_panel)

    # # Display formatted results in a panel
    # display_formatted_results(
    #     cleaned_tool_message=f"AP News Articles about: {search_query}",
    #     title=f"AP News Articles about: {search_query}",
    #     tool_name="get_latest_news_from_AP",
    #     tool_params={"search_query": search_query},
    #     citations=citations,
    #     beacon_tool_source="AP",
    #     showFull=True
    # )

    return format_articles_tool_result(
        articles=result.articles,
        citations=citations,
        tool_name="get_latest_news_from_AP",
        tool_params={"search_query": search_query},
        beacon_tool_source="AP"
    )

@tool
async def get_combined_news(search_query: str) -> RULAC_TOOL_RESULT:
    """
    Retrieves news articles from multiple sources (BBC, Al Jazeera, AP, Reuters) in parallel based on the provided search query.
    Articles from all sources are combined, then sorted chronologically by publication date.
    
    The function works in phases:
    1. Run all news retrieval tasks in parallel using asyncio
    2. Collect and standardize article data from all sources
    3. Sort articles by publication date (with fallback to source sorting)
    4. Generate combined output with all articles in chronological order
    
    :param search_query: The search query to find relevant news articles
    :return: A dictionary with "articles" containing the combined article summaries and "citations" list
    """
    # Start timing the entire process
    start_time = time.time()
    
    # Display initial message with the search query
    log(f"STARTING COMBINED NEWS SEARCH: '{search_query}'", "title")
    
    # Initialize containers for the final output
    all_citations = []
    
    try:
        # PHASE 1: PARALLELIZE NEWS RETRIEVAL FROM ALL SOURCES
        log("Fetching news articles from all sources in parallel...", "debug")
        parallel_start_time = time.time()
        
        # Create tasks for all news sources
        tasks = [
            get_latest_news_from_BBC.ainvoke({"search_query": search_query}),
            get_latest_news_from_AlJazeera.ainvoke({"search_query": search_query}),
            get_latest_news_from_AP.ainvoke({"search_query": search_query}),
            get_latest_news_from_Reuters.ainvoke({"search_query": search_query})
        ]
        
        # Run all news retrieval tasks in parallel 
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_names = ["BBC", "Al Jazeera", "AP", "Reuters"]
                log(f"Error retrieving news from {source_names[i]}: {str(result)}", "error")
            else:
                valid_results.append(result)
        
        parallel_elapsed = time.time() - parallel_start_time
        log(f"Parallel retrieval completed in {parallel_elapsed:.2f} seconds", "debug")
        
        # PHASE 2: PROCESS RESULTS FROM ALL SOURCES
        all_articles_unsorted = []  # List to hold all ArticleSummary objects
        all_articles_sorted = []    # List to hold all ArticleSummary objects
        all_sources = set()         # Track all source names
        
        # Collect all articles and citations from each source
        for result in valid_results:
            # Extract articles from each source's results
            if "articles" in result:
                # With our new structure, articles should be directly available
                all_articles_unsorted.extend(result["articles"])
                
                # Add source names to our set
                for article in result["articles"]:
                    all_sources.add(article.source)
            
            # Collect citations
            if "citations" in result:
                all_citations.extend(result["citations"])
        
        # Log article collection summary
        log(f"Collected a total of {len(all_articles_unsorted)} articles from all sources", "success")
        
        # Debug: Add date type checking before sorting
        if logger.isEnabledFor(logging.DEBUG) and all_articles_unsorted:
            log("Checking article date types before sorting:", "debug")
            date_types = {}
            for i, article in enumerate(all_articles_unsorted[:min(10, len(all_articles_unsorted))]):
                date_type = type(article.date).__name__
                date_types[date_type] = date_types.get(date_type, 0) + 1
                log(f"Article {i+1} from {article.source}: Date '{article.date}' has type {date_type}", "debug")
            
            log(f"Date type summary before sorting: {date_types}", "debug")
            
            # If we have mixed types, try to standardize them to prevent comparison errors
            if len(date_types) > 1:
                log("Detected mixed date types - standardizing to strings", "warning")
                for article in all_articles_unsorted:
                    if isinstance(article.date, datetime):
                        # Convert datetime to string
                        article.date = article.date.strftime("%Y-%m-%d %H:%M:%S")
                        log(f"Converted datetime to string: {article.date}", "debug")
        
        # PHASE 3: SORT ARTICLES BY DATE
        if all_articles_unsorted:
            log(f"Sorting {len(all_articles_unsorted)} articles by publication date...", "debug")
            
            # Normalize date types to prevent comparison errors
            for article in all_articles_unsorted:
                # If date is a datetime object, convert to string to maintain consistent types
                if isinstance(article.date, datetime):
                    article.date = article.date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Helper function to parse and standardize dates for sorting
            def get_sortable_date(article):
                date_str = article.date
                
                # If it's already a datetime object, just return it
                if isinstance(date_str, datetime):
                    return date_str
                
                # If it's None or empty, return a very old date for sorting purposes
                if not date_str:
                    return datetime.min
                
                try:
                    # Try to convert to a standard datetime format for comparison
                    for fmt in [
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                        "%d %b %Y",
                        "%B %d, %Y",
                        "%b %d, %Y"
                    ]:
                        try:
                            return datetime.strptime(date_str.strip(), fmt)
                        except ValueError:
                            continue
                    
                    # If no format matches, try a more lenient approach with dateutil
                    try:
                        from dateutil import parser
                        return parser.parse(date_str)
                    except (ImportError, ValueError, TypeError):
                        pass
                    
                    # If all fails, return a string (this will still cause comparison issues,
                    # but at least we tried all parsing methods)
                    return date_str
                except Exception as e:
                    log(f"Error processing date '{date_str}': {str(e)}", "error")
                    # Fallback to string (may cause comparison errors)
                    return date_str
            
            # Try to sort articles by date
            try:
                all_articles_sorted = all_articles_unsorted.copy()  # Create a copy to sort
                
                # Log a few sample articles before sorting
                if all_articles_sorted and logger.isEnabledFor(logging.DEBUG):
                    log("Sample of articles before sorting:", "debug")
                    for i, article in enumerate(all_articles_sorted[:3]):
                        log(f"Article {i+1}: Title: {article.title[:30]}..., Date: {article.date} (Type: {type(article.date).__name__})", "debug")
                
                all_articles_sorted.sort(key=get_sortable_date)  # Sort in-place
                log("Articles sorted successfully by date", "success")
            except Exception as e:
                log(f"Could not sort articles by date: {str(e)}", "error")
                
                # Add more detailed error logging
                if logger.isEnabledFor(logging.DEBUG):
                    import traceback
                    log(f"Detailed sort error: {traceback.format_exc()}", "error")
                    
                    # Analyze the article dates
                    log("Analyzing article dates to find inconsistencies:", "debug")
                    date_types = {}
                    for i, article in enumerate(all_articles_unsorted[:10]):  # Check first 10 articles
                        date_type = type(article.date).__name__
                        date_types[date_type] = date_types.get(date_type, 0) + 1
                        log(f"Article {i+1}: Date '{article.date}' has type {date_type}", "debug")
                    
                    log(f"Date type summary: {date_types}", "debug")
                
                # If date sorting fails, try sorting by source
                try:
                    all_articles_sorted = all_articles_unsorted.copy()  # Create a copy to sort
                    all_articles_sorted.sort(key=lambda x: x.source)  # Sort in-place
                    log("Articles sorted by source as fallback", "debug")
                except Exception:
                    log("Could not sort articles - keeping original order", "debug")
                    all_articles_sorted = all_articles_unsorted  # Use original order as fallback

            # PHASE 4: DISPLAY ARTICLE INFO
            # Display a summary of what we found
            log(f"Retrieved {len(all_articles_sorted)} recent news articles from {len(all_sources)} sources", "success")
            
            # Display a sample of articles if debug mode is enabled
            if logger.isEnabledFor(logging.DEBUG):
                for idx, article in enumerate(all_articles_sorted[:3]):  # Show first 3 articles
                    human_readable_date = convert_to_human_readable_date(article.date)
                    article_panel = Panel(
                    f"[bold]Title:[/bold] {article.title}\n"
                    f"[bold]Date:[/bold] {human_readable_date}\n"
                    f"[bold]Source:[/bold] {article.source}",
                    title=f"Article {idx+1} of {len(all_articles_sorted)}",
                    border_style="blue"
                    )
                    console.print(article_panel)
                
                if len(all_articles_sorted) > 3:
                    log(f"...and {len(all_articles_sorted) - 3} more articles", "debug")
                
            # Create citations using the new helper function
            all_citations = [create_citation_for_article(article) for article in all_articles_sorted]
            
        else:
            # No articles found
            log("No relevant news articles found for this query.", "error")
            all_articles_sorted = []

        # Log summary statistics
        total_elapsed = time.time() - start_time
        log(f"Combined parallel news processing completed in {total_elapsed:.2f} seconds", "success")
        log(f"Total articles: {len(all_articles_sorted)} | Total citations: {len(all_citations)}", "success")

        # Display formatted results
        summary_content = f"Latest news and developments related to '{search_query}' includes {len(all_articles_sorted)} articles, listed in chronological order (oldest first):"

        # for each article, we will add it to summary_content
        for article in all_articles_sorted:
            # Convert date to human-readable format
            human_readable_date = convert_to_human_readable_date(article.date)
            summary_content += f"\n\n#### {article.title} "
            summary_content += f"\nSource: {article.source}"
            summary_content += f"\nPublication Date: {human_readable_date}"
            summary_content += f"\n{article.content}"
        
        # Display formatted results if debug mode is enabled
        if logger.isEnabledFor(logging.DEBUG):
            display_formatted_results(
                cleaned_tool_message=summary_content,
                title=f"COMBINED NEWS ARTICLES",
                tool_name="get_combined_news",
                tool_params={"search_query": search_query},
                citations=all_citations,
                beacon_tool_source="Multiple News Sources",
                showFull=False
            )
        
        # Return formatted result with articles array
        return format_standard_tool_result(
            content=summary_content,
            citations=all_citations,
            tool_name="get_combined_news",
            tool_params={"search_query": search_query},
            beacon_tool_source="Multiple News Sources"
        )
        
    except Exception as e:
        error_message = f"Error in combined news processing: {str(e)}"
        log(error_message, "error")
        logger.error(f"Full error details: {traceback.format_exc()}")
        
        # Return error result
        return format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name="get_combined_news",
            tool_params={"search_query": search_query},
            beacon_tool_source="Multiple News Sources"
        )

async def summarize_individual_article(
    chat: ChatGroq,
    title: str,
    date: str,
    content: str,
    source_name: str,
    url: str
) -> Optional[ArticleSummary]:
    """
    Summarize an individual article using Groq API with instructor for validation.
    
    Args:
        chat: Initialized ChatGroq instance
        title: Article title
        date: Publication date
        content: Article content
        source_name: Name of the news source
        url: URL of the article
        
    Returns:
        ArticleSummary object or None if summarization failed
    """
    try:
        start_time = time.time()
        
        # Create a smaller, focused XML structure for just this article
        article_xml = f"""<article><title>{title}</title><publication_date>{date}</publication_date><content>{content}</content></article>"""
        
        # Define our Pydantic model for the summary response
        class ArticleSummarySchema(BaseModel):
            title: str = Field(..., description="The original or improved title of the article")
            date: str = Field(..., description="The publication date of the article")
            summary: str = Field(..., description="A concise, factual summary of the article contents with essential details, figures, and key quotes. Should be 3+ paragraphs.")
        
        # Initialize Groq client with instructor
        groq_client = groq.AsyncGroq(api_key=tool_specific_values["GROQ_API_KEY"])
        client = instructor.from_groq(groq_client)
        
        # Create system prompt for article summarization
        system_prompt = f"""
You are an expert news analyzer that produces structured output.
Your task is to analyze and summarize a news article, focusing on the most important information and maintaining objectivity, including key figures and quotes as found in the article.

The news article to summarize is contained in the <content> tag:
{article_xml}

You should return json according to the following schema, including all fields:
{ArticleSummarySchema.model_json_schema()}

"""
        
        # User message to explicitly request the summary
        user_prompt = "Please provide a detailed, factual summary of this article in 3+ paragraphs."
        
        # Make API call using instructor for automatic parsing and validation
        try:
            validated_response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_model=ArticleSummarySchema
            )
            
            # Sanitize the summary by removing newlines
            sanitized_summary = validated_response.summary.replace('\n', ' ').replace('\r', ' ')
            
            # Create ArticleSummary object with validated data
            article_summary = ArticleSummary(
                title=validated_response.title,
                date=validated_response.date,
                content=sanitized_summary,
                original_content=content,  # Store the original content for citation purposes
                url=url,
                source=source_name
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Summarized article in {elapsed:.2f} seconds: {title[:50]}...")
            
            return article_summary
            
        except Exception as validation_error:
            # If instructor validation fails, log the error
            logger.error(f"Instructor validation error: {str(validation_error)}")
            raise
            
    except Exception as e:
        log(f"Error summarizing article: {str(e)}", "error")
        logger.error(f"Error type: {type(e).__name__}")
        logger.debug(f"Exception details: {traceback.format_exc()}")
        
        # Create a fallback summary with the original title and date
        try:
            fallback_message = "Article content could not be summarized properly. Please refer to the original source."
            return ArticleSummary(
                title=title,
                date=date,
                content=fallback_message,
                original_content=content,  # Store the original content even for fallback cases
                url=url,
                source=source_name
            )
        except:
            return None

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
        
        # Update API keys with loaded environment variables
        groq_key = os.getenv("GROQ_API_KEY_NEWS") or os.getenv("GROQ_API_KEY", "")
        brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        
        if groq_key and brave_key:
            set_api_keys(groq_api_key=groq_key, brave_api_key=brave_key)
            print(f"✓ API keys loaded successfully")
            print(f"  - Groq key length: {len(groq_key)}")
            print(f"  - Brave key length: {len(brave_key)}")
        else:
            if not groq_key:
                print("⚠ Warning: GROQ_API_KEY not found in environment")
            if not brave_key:
                print("⚠ Warning: BRAVE_SEARCH_API_KEY not found in environment")
            
    except ImportError:
        print("⚠ Warning: python-dotenv not installed. Install with: pip install python-dotenv")
        print("  Or export environment variables manually before running")
    
    async def run_tests():
        """Run all test functions"""
        log("STARTING NEWS TOOLS TESTS", "title")
        
        # Test scenarios for news sources
        news_test_scenarios = [
            {
                "name": "Get News about deepseek",
                "params": {
                    "search_query": "deepseek"
                },
            },
            # {
            #     "name": "Get News about Technology",
            #     "params": {
            #         "search_query": "artificial intelligence drone"
            #     },
            # },
            # {
            #     "name": "Get News about Ukraine War",
            #     "params": {
            #         "search_query": "ukraine ceasefire"
            #     },
            # },
            # {
            #     "name": "Get News about Ukraine conflict",
            #     "params": {
            #         "search_query": "ukraine conflict"
            #     },
            # },
            # {
            #         "name": "Get Combined News",
            #         "params": {
            #             "search_query": "trump and DOGE"
            #         }
            #     }
            {
                "name": "Get News about lgbt rights in USA",
                "params": {
                    "search_query": "LGBT rights in the USA"
                },
            }
        ]

        # # Use the standardized test framework
        # await standardized_tool_test(
        #     tool_function=get_latest_news_from_BBC,
        #     test_scenarios=news_test_scenarios,
        #     test_title="BBC News Retrieval Tool Test"
        # )

        # await standardized_tool_test(
        #     tool_function=get_latest_news_from_AlJazeera,
        #     test_scenarios=news_test_scenarios,
        #     test_title="Al Jazeera News Retrieval Tool Test"
        # )

        # # Uncomment Reuters test
        # await standardized_tool_test(
        #     tool_function=get_latest_news_from_Reuters,
        #     test_scenarios=news_test_scenarios,
        #     test_title="Reuters News Retrieval Tool Test"
        # )

        # await standardized_tool_test(
        #     tool_function=get_latest_news_from_AP,
        #     test_scenarios=news_test_scenarios,
        #     test_title="AP News Retrieval Tool Test"
        # )
        
  
        
        # Test the new get_combined_news tool
        await standardized_tool_test(
            tool_function=get_combined_news,
            test_scenarios=news_test_scenarios,
            test_title="Combined News Retrieval Tool Test"
        )
       

        log("ALL TESTS COMPLETED", "success")
    
    # Run the async test function
    asyncio.run(run_tests()) 


