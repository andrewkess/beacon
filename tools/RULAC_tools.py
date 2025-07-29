from typing import List, Dict, Any, Union, Optional
from typing_extensions import TypedDict
from langchain_core.tools import tool
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text
from rich.markdown import Markdown
from langchain_neo4j import Neo4jGraph
import json
import logging
import os
import coloredlogs
import asyncio
from langchain_core.messages import AIMessage
from fake_useragent import UserAgent
import re
from urllib.parse import urlparse, urljoin
import unicodedata
import time

# Define Citation type using TypedDict
class Citation(TypedDict):
    """
    TypedDict for standardized citation format used throughout RULAC tools.
    
    Attributes:
        title: The title of the citation/source to be displayed in UI as visible SOURCE (e.g. "RULAC - Military Occupation of Ukraine")
        url: The URL to the source
        formatted_content: The formatted content behind the citation, public facing and used for display purposes in UI
    """
    title: str
    url: str
    formatted_content: str

# Define RULAC_TOOL_RESULT type using TypedDict
class RULAC_TOOL_RESULT(TypedDict):
    """
    TypedDict for standardized RULAC tool result format used throughout RULAC tools.
    
    Attributes:
        content: The main content of the results (can be a string, list, or dictionary)
        citations: List of citation dictionaries
        tool_use_metadata: Information about tool usage including name and parameters
    """
    content: Union[str, List[Dict[str, Any]], Dict[str, Any]]
    citations: List[Citation]
    tool_use_metadata: Optional[Dict[str, Any]]

# Global configuration values
tool_specific_valves = {
    "NEO4J_URL": "bolt://neo4j-arm:7687",
    "NEO4J_TESTING_URL": "bolt://localhost:7687",
    "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": "password",
}

# Initialize Rich Console
console = Console()

# Configure logging, but only when running directly
logger = logging.getLogger("Argos")

# Only set the level when this module is run directly, not when imported
if __name__ == "__main__":
    coloredlogs.install(
        logger=logger,
        level="INFO",
        isatty=True,
        fmt="%(asctime)s [%(levelname)s] %(message)s",
    )
else:
    # When imported, don't override the parent logging configuration
    # Just get a reference to the logger without changing level
    pass

# === NEW STANDARDIZED HELPER FUNCTIONS ===

def create_standard_citation(
    title: str, 
    url: str, 
    formatted_content: str = ""
) -> Citation:
    """
    Create a standard citation dictionary that can be used by the OpenWebUI event emitter UI
    
    Args:
        title (str): The title of the citation
        url (str): The URL to the source
        formatted_content (str, optional): The formatted content to include in the citation. Defaults to empty string.
    
    Returns:
        Citation: A dictionary containing citation information
    """
    logger.debug(f"Creating standard citation for: {title}")

    # Return Citation TypedDict with the three required fields
    return {
        "title": title,
        "url": url,
        "formatted_content": formatted_content
    }


def format_standard_tool_result(
    content: Union[str, List[Dict[str, Any]], Dict[str, Any]], 
    citations: List[Citation],
    tool_name: Optional[str] = None,
    tool_params: Optional[Dict[str, Any]] = None,
    beacon_tool_source: str = "RULAC"
) -> RULAC_TOOL_RESULT:
    """
    Format tool results in a standardized structure.
    
    Args:
        content (Union[str, List[Dict[str, Any]], Dict[str, Any]]): The main content of the results
        citations (List[Citation]): List of citation dictionaries
        tool_name (Optional[str]): Name of the tool being used
        tool_params (Optional[Dict[str, Any]]): Parameters used for the tool call
        beacon_tool_source (str): Source of the tool ("RULAC", "WEB", etc.). Defaults to "RULAC".
    
    Returns:
        RULAC_TOOL_RESULT: A standardized result dictionary
    """
    logger.debug("Formatting standard tool result")
    
    # Create tool use metadata if either tool_name or tool_params is provided
    tool_use_metadata = None
    if tool_name or tool_params:
        tool_use_metadata = {
            "tool_source": beacon_tool_source,
            "tool_name": tool_name,
            "tool_params": tool_params or {}
        }
    
    result: RULAC_TOOL_RESULT = {
        "content": content,
        "citations": citations,
        "tool_use_metadata": tool_use_metadata
    }
    
    return result
    
async def standardized_tool_test(
    tool_function: callable, 
    test_scenarios: List[Dict[str, Any]],
    test_title: str = "RULAC Tool Test"
) -> None:
    """
    Run standardized tests on a RULAC tool function.
    
    Args:
        tool_function (callable): The tool function to test
        test_scenarios (List[Dict[str, Any]]): List of test scenarios with parameters
        test_title (str, optional): Title for the test. Defaults to "RULAC Tool Test".
    """
    console.print(Panel(f"[bold]{test_title}[/]", style="bold white on blue", border_style="blue"))
    
    for scenario in test_scenarios:
        scenario_name = scenario.get("name", "Unnamed Test Scenario")
        
        try:
            # Track execution time
            start_time = time.time()
            
            # Extract parameters
            params = scenario["params"]
            
            # For LangChain tools, we need to properly format input
            if hasattr(tool_function, "ainvoke"):
                # Pass the params dictionary directly to ainvoke
                results = await tool_function.ainvoke(params)
            else:
                # For regular async functions, use normal call
                results = await tool_function(**params)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Success message
            console.print(f"[green]✓ Test completed in {execution_time:.2f} seconds[/]")
            
            # We don't need to preview results here as they will be displayed
            # in the INFO panel during tool execution
            
        except Exception as e:
            # Failure message
            console.print(f"[red]✗ Test failed: {str(e)}[/]")
            logger.error(f"Test failed for {scenario_name}: {str(e)}")
    
    console.print(f"\n[bold green]All tests completed for {test_title}[/]")

# Global Neo4j graph connection
graph = None

def initialize_neo4j(local_testing=False):
    """Initialize the Neo4j graph connection using configuration values"""
    global graph
    
    # If graph is already initialized, just return it
    if graph is not None:
        return graph
    
    # Dynamically switch Neo4j URL based on the testing flag
    neo4j_url = tool_specific_valves["NEO4J_TESTING_URL"] if local_testing else tool_specific_valves["NEO4J_URL"]
    neo4j_username = tool_specific_valves["NEO4J_USERNAME"]
    neo4j_password = tool_specific_valves["NEO4J_PASSWORD"]
    
    # Debugging: Neo4j connection
    print(f"DEBUG: Connecting to Neo4j at {neo4j_url} with username {neo4j_username}")
    
    try:
        # Connect to Neo4j using the provided credentials
        graph = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password,
            enhanced_schema=False,
        )
        return graph
    except Exception as conn_error:
        error_msg = f"Error connecting to Neo4j: {conn_error}"
        logger.error(error_msg)
        raise Exception(error_msg) from conn_error

# Initialize the Neo4j connection once at module load time
try:
    # Default to local testing mode which uses localhost Neo4j
    # This can be overridden when the function is called
    if os.path.exists("/app/backend/beacon_code"):
        graph = initialize_neo4j(local_testing=False)
    else:
        graph = initialize_neo4j(local_testing=True)
    print("DEBUG: Neo4j connection initialized successfully")
except Exception as e:
    print(f"WARNING: Failed to initialize Neo4j on module load: {e}")
    print("Tools requiring Neo4j will attempt to reconnect when used")


class HelpFunctions:
    def get_base_url(self, url):
        """Extract base URL from full URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def remove_emojis(self, text):
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


# # Load Beacon public files from local files if os path doesnt exist
# else:
try:

        # system prompts

        # Final System Prompts for General and Tool Agents
        from prompts.indv_tool_prompts import tool_cypher_RULAC_conflict_by_StateActor
        from prompts.indv_tool_prompts import tool_cypher_RULAC_conflict_by_NonStateActor
        from prompts.indv_tool_prompts import tool_cypher_RULAC_conflict_taking_place_country
        from prompts.indv_tool_prompts import tool_cypher_RULAC_conflict_by_org
        from prompts.indv_tool_prompts import tool_cypher_RULAC_conflict_by_Region
        from prompts.indv_tool_prompts import baselineRULACinfo
        from prompts.indv_tool_prompts import baselineClassificationMethodology
        from prompts.indv_tool_prompts import baselineIHLLegalFramework
        from prompts.indv_tool_prompts import baselineARGOSinfo

except Exception as e:
        print("DEBUG: Error importing code and functions:", e)
        raise


def substitute_params(query: str, params: dict) -> str:
    """Return a debug version of the query with parameters substituted as strings."""
    debug_query = query
    for key, value in params.items():
        # Convert the value to its JSON representation so that lists/strings are properly quoted.
        debug_value = json.dumps(value)
        debug_query = debug_query.replace(f"${key}", debug_value)
    return debug_query


def process_rulac_data(data: dict, research_task: str = "No task provided") -> tuple[str, List[Citation]]:
    """
    Processes RULAC research data by formatting it into a human-readable markdown string
    and extracting citation information. 
    
    Args:
        data: The research data dictionary retrieved from Neo4j
        research_task: The research task that was used to retrieve the data (defaults to "No task provided")
    
    Returns:
        tuple[str, List[Citation]]: A tuple containing (formatted_content, citations)
            - formatted_content: Formatted markdown string with the research results
            - citations: A list of citation dictionaries
    """
    logger.debug("Processing RULAC data: formatting and collecting citations")
    
    # ----- FORMATTING CONTENT -----
    # Extract the summary if present
    summary = data.get("summary", "No summary available.")
    
    # Extract and format conflicts
    formatted_conflicts_for_final_output = []
    conflicts = data.get("conflict_details", [])
    
    # ----- COLLECTING CITATIONS -----
    citations: List[Citation] = []
    
    for conflict in conflicts:
        # Format conflict details, one version for citation and one for eventual system prompt

        formatted_for_citation = (
            f"{conflict.get('conflict_name', 'Unnamed Conflict')}\n\n"
            f"Conflict Classification under IHL: {conflict.get('conflict_classification', 'N/A')}\n\n"
            f"Overview: {conflict.get('conflict_overview', 'N/A')}\n\n"
            f"Applicable IHL Law: {conflict.get('applicable_ihl_law', 'N/A')}\n\n"
            f"State Parties: {conflict.get('state_parties', 'None recorded')}\n\n"
            f"Non-State Parties: {conflict.get('non_state_parties', 'None recorded')}"
            # f"Source Citation: {conflict.get('conflict_citation', 'No Citation Available')}\n"
        )

        formatted_for_system_prompt = (
            f"##### Conflict Name: {conflict.get('conflict_name', 'Unnamed Conflict')}\n"
            f"Conflict Classification under IHL: {conflict.get('conflict_classification', 'N/A')}\n"
            f"Overview: {conflict.get('conflict_overview', 'N/A')}\n"
            f"Applicable IHL Law: {conflict.get('applicable_ihl_law', 'N/A')}\n"
            f"State Parties: {conflict.get('state_parties', 'None recorded')}\n"
            f"Non-State Parties: {conflict.get('non_state_parties', 'None recorded')}"
        )

        formatted_conflicts_for_final_output.append(formatted_for_system_prompt)
        
        # Create citation for this conflict
        if "conflict_citation" in conflict and "conflict_name" in conflict:
            citation = create_standard_citation(
                title="RULAC - " + conflict.get("conflict_name", "Unnamed Conflict"),
                url=conflict.get("conflict_citation", "https://www.rulac.org"),
                formatted_content=formatted_for_citation
            )
            citations.append(citation)
    
    all_combined_conflicts_for_final_output = "\n\n".join(formatted_conflicts_for_final_output) if formatted_conflicts_for_final_output else "No conflict details available."
    
    formatted_output = (
        # output a human readable of the query that was used to generate the RULAC research
        f"### {research_task}\n\n"
        f"{summary}\n\n"
        f"#### Conflict profiles\n\n"
        f"{all_combined_conflicts_for_final_output}"
    )
    
    # Add a summary citation if needed
    if not citations and "summary" in data:
        # Add a fallback general citation if no specific conflict citations were found
        citation = create_standard_citation(
            title="RULAC",
            url="https://www.rulac.org",
            formatted_content=summary
        )
        citations.append(citation)
    
    return formatted_output, citations



def display_formatted_results(cleaned_tool_message, title="RULAC CLEANED TOOL RESULTS", tool_name=None, tool_params=None, citations: Optional[List[Citation]]=None, beacon_tool_source: str = "RULAC", showFull: bool = False):
    """
    Displays a formatted panel with the cleaned tool results.
    
    Args:
        cleaned_tool_message: The formatted tool message to display
        title: The title for the panel (defaults to "RULAC CLEANED TOOL RESULTS")
        tool_name: The name of the tool being used (optional)
        tool_params: Dictionary of parameters used for the tool call (optional)
        citations: List of citation dictionaries (optional). If provided, these will be displayed.
        beacon_tool_source: Source of the tool ("RULAC", "WEB", etc.). Defaults to "RULAC".
        showFull: When True, displays the full message content. When False (default), shows only the first 500 characters.
    """
    
    # Only display results if logging level is DEBUG or INFO
    if logger.getEffectiveLevel() > logging.INFO:
        return
        
    content = cleaned_tool_message
    # Only extract citations from message if not provided directly
    if citations is None:
        if isinstance(cleaned_tool_message, list):
            # Handle old format (list of results)
            content = []
            citations: List[Citation] = []
            
            for item in cleaned_tool_message:
                if isinstance(item, dict):
                    if "name" in item:
                        content.append(item)
                        if "link" in item:
                            citations.append({
                                "title": item["name"],
                                "url": item["link"],
                                "source": "RULAC Database",
                                "type": "reference"
                            })
                    elif "content" in item:
                        # File-based tool result
                        content = item["content"]
                        if "url" in item and "title" in item:
                            citations.append({
                                "title": item["title"],
                                "url": item["url"],
                                "source": "RULAC Website",
                                "type": "reference"
                            })
        else:
            # Handle string content with no citations provided
            citations: List[Citation] = []
    
    # Create tool_use_metadata if needed
    tool_use_metadata = None
    if tool_name or tool_params:
        tool_use_metadata = {
            "tool_source": beacon_tool_source,
            "tool_name": tool_name,
            "tool_params": tool_params or {}
        }
    
    # Create standardized result
    result: RULAC_TOOL_RESULT = {
        "content": content,
        "citations": citations,
        "tool_use_metadata": tool_use_metadata
    }
    
    # Display results using standardized approach
    # Determine whether to show the full content or a truncated version
    display_content = str(cleaned_tool_message)
    word_count_of_content = len(display_content.split())

    if not showFull and len(display_content) > 500:
        display_content = display_content[:500] + "..."
    
    # Create a Text object with the content
    text_content = Text(display_content)
    
    # Add XML tag highlighting
    for match in re.finditer(r'<[^>]+>', display_content):
        start, end = match.span()
        text_content.stylize("bold cyan", start, end)
        
    results_panel = Panel(
        text_content,
        style="green on white",
        border_style="black",
        title=f"[TOOL INFO] {title}" + (" [FULL]" if showFull else ""),
        title_align="left",
        expand=True,
    )            
    # temporary disable results panel
    console.print(results_panel)
    
    # If citations are present, display a blue citations panel
    if citations:
        # Count total citations
        citation_count = len(citations)
        
        # Format citations as a list with checkmarks
        citation_list = f"{citation_count} citations collected"
        for citation in citations:
            # Extract just the hostname and path from the URL
            url = citation.get('url', '')
            parsed_url = urlparse(url)
            display_url = f"{parsed_url.netloc}{parsed_url.path}"
            
            # Get the citation title
            title = citation.get('title', 'Unknown')
            
            # Add a checkmark for each citation with title and URL
            citation_list += f"\n✓ {title} - {display_url}"
        
        citations_panel = Panel(
            citation_list,
            style="white on blue",
            border_style="blue",
            title="[CITATIONS]",
            title_align="left",
        )
        console.print(citations_panel)

    # If tool information was provided, display a blue tool info panel
    if tool_use_metadata:
        # Create formatted params string if params exist
        params_str = ""
        if tool_params:
            params_str = "\n\nParameters:"
            for key, value in tool_params.items():
                if isinstance(value, list):
                    if len(value) > 0:
                        params_str += f"\n- {key}: {', '.join(str(v) for v in value)}"
                    else:
                        params_str += f"\n- {key}: []"
                else:
                    params_str += f"\n- {key}: {value}"
        
        # Create the tool info panel
        tool_info_panel = Panel(
            f"Tool: {tool_name or 'Unknown'}\nSource: {tool_use_metadata.get('tool_source', 'RULAC')}{params_str}\nWord Count: {word_count_of_content}",
            style="white on blue",
            border_style="blue",
            title="[TOOL EXECUTION DETAILS]",
            title_align="left",
            expand=False,
        )
        console.print(tool_info_panel)# Create standardized result structure for compatibility



def truncate_to_n_words(text, token_limit):
    tokens = text.split()
    truncated_tokens = tokens[:token_limit]
    return " ".join(truncated_tokens)


def get_base_url(url):
    """Extract base URL from full URL."""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return base_url

def generate_excerpt(content, max_length=200):
    """
    Generate a clean excerpt from content, truncating properly at word boundaries 
    and removing excess whitespace.
    """
    if not content:
        return ""
        
    # Clean up the content
    clean_content = re.sub(r'\s+', ' ', content).strip()
    
    # Return full content instead of truncated excerpt
    return clean_content

def remove_emojis(text):
    """Remove emojis from text."""
    if not text:
        return ""
    return "".join(c for c in text if not unicodedata.category(c).startswith("So"))




# TOOLS

@tool
async def get_armed_conflict_data_by_country(
    countries: List[str],
    conflict_types: List[str],
) -> RULAC_TOOL_RESULT:
    """
    Retreives armed conflict data from RULAC (Rule of Law in Armed Conflict) for one or more countries. 
    
    Conflict data returned includes: conflict name, conflict overview, applicable international humanitarian law, conflict classification, and a list of state actors and non-state actors to the conflict. 

    This tool retreive all conflicts per country by default, but can also use an optional filter by conflict classification type. Note: There are only three valid conflict classifications, as defined by RULAC: "International Armed Conflict (IAC)", "Non-International Armed Conflict (NIAC)", "Military Occupation".

    ## Steps
    1. Identify the country or countries to retreive conflict data for
    2. Identify any conflict classification filters to apply, if requested. By default, return an empty [] for conflict_types to retrieve all conflicts per country.


    ## Example Tool Call Parameters
    
    Example question:"What IAC and Military Occupation conflicts involve France and Russia?"
    countries: ["France", "Russia"]
    conflict_types: ["International Armed Conflict (IAC)", "Military Occupation"]

    Example question:"What conflicts is USA a party to and what IHL law applies?"
    countries: ["United States of America"]
    conflict_types: []

    Example question:"What conflicts are taking place in the Democratic Republic of Congo (DRC)?"
    countries: ["Democratic Republic of Congo"]
    conflict_types: []

    :param countries: List of country names to retrieve conflict data for
    :param conflict_types: List of conflict classification types to filter by in query
    
    :return: A dictionary with "result" string containing the formatted research data and "citations" list of citation objects
    """
    tool_name = "get_armed_conflict_data_by_country"
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    # Make sure Neo4j is connected
    global graph
    if graph is None:
        # Try to initialize the connection
        # print("Initializing Neo4j connection... make sure it only happens once here ...")
        graph = initialize_neo4j(local_testing=True)
        
    # Create research task from parameters
    research_task = f"RULAC armed conflict data by country ({', '.join(countries)})" + (f" with conflict classification ({', '.join(conflict_types)})" if conflict_types else "")
    # Prepare the parameters for the query
    params = {
        "countries": countries,  # Keep the internal parameter name the same for compatibility
        "conflict_types": conflict_types,  # Keep the internal parameter name the same for compatibility
        "research_task": research_task
    }

    # Load tool-specific cypher template
    TOOL_PROMPT = tool_cypher_RULAC_conflict_by_StateActor.PROMPT

    # DEBUGGING section
    debug_query = substitute_params(TOOL_PROMPT, params)
    if logger.getEffectiveLevel() == logging.DEBUG:
            panel = Panel(
                Markdown(debug_query),
                border_style="blue",
                title="[TOOL DEBUGGING] Cypher Prompt dynamically compiled for NEO4J",
                title_align="left",
                expand=True,
            )            
            console.print(panel)

    try:
        # Execute the query using the graph.query() method
        results = graph.query(TOOL_PROMPT, params)
        if not results:
            logger.warning("No RULAC data found.")
            
            # Format empty result
            empty_result = format_standard_tool_result(
                content="No RULAC conflict data found for the specified countries and conflict types.",
                citations=[], # Empty List[Citation]
                tool_name=tool_name,
                tool_params=params
            )
            
            # Display "no results" message with tool info
            display_formatted_results(
                "No RULAC conflict data found for the specified countries and conflict types.",
                title="RULAC Search: No Results",
                tool_name=tool_name,
                tool_params=params
            )
            
            # Print end marker for tool execution, as debug log
            logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (with empty result)\n" + 
                         "="*50 + "[/bold white]\n")
            
            return empty_result

        # IF there are results, format the result content
        # Assume the first record contains the required RULAC_research field   
        research_result = results[0].get("RULAC_research")
        
        # Process the result data - formatting content and collecting citations in one step
        formatted_content, citations = process_rulac_data(research_result, research_task)

        # Format the standardized result
        result = format_standard_tool_result(
            content=formatted_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
        display_formatted_results(
            formatted_content, 
            title=f"RULAC Conflicts Involving Countries", 
            tool_name=tool_name, 
            tool_params=params, 
            citations=citations,
            showFull=False  # Show full content for this comprehensive report
        )

        # Print end marker for tool execution, as debug log
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return result

    except Exception as e:
        error_message = f"Error retrieving RULAC data: {str(e)}"
        logger.error(error_message)
        
        # Format error result
        error_result = format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )
        
        # Display error message with tool info
        display_formatted_results(
            error_message,
            title="RULAC Search: Error",
            tool_name=tool_name,
            tool_params=params,
            citations=[]
        )
        
        # Print end marker for tool execution, as debug log
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                    f"ENDING TOOL: {tool_name} (with error)\n" + 
                    "="*50 + "[/bold white]\n")
        
        return error_result

@tool
async def get_armed_conflict_data_by_non_state_actor(
    non_state_actors: List[str],
) -> RULAC_TOOL_RESULT:
    """
    Retreives armed conflict data from RULAC (Rule of Law in Armed Conflict) by one or more non-state actors. 
    
    Conflict data returned includes: conflict name, conflict overview, applicable international humanitarian law, conflict classification, and a list of state actors and non-state actors to the conflict. 

    This tool retrieves all conflicts involving the specified non-state actors. The tool accepts various spellings, aliases, and acronyms for each non-state actor to ensure comprehensive data retrieval.

    ## Steps
    1. Identify the non-state actor(s) to retrieve conflict data for
    2. Provide a list of alternative spellings, aliases, and acronyms for each non-state actor to ensure comprehensive data retrieval


    ## Example Tool Call Parameters
    
    Example question:"What conflicts involve Hezbollah?"
    non_state_actors: ["Hezbollah", "Hizbollah", "Hizbullah", "Hizballah", "Party of God"]

    Example question:"What conflicts involve ISIS?"
    non_state_actors: ["ISIS", "Islamic State", "Daesh"]

    Example question:"What conflicts involve FARC?"
    non_state_actors: ["Revolutionary Armed Forces of Colombia (FARC)", "Revolutionary Armed Forces", "FARC", "Fuerzas Armadas Revolucionarias de Colombia"]

    :param non_state_actors: List of spellings, aliases, and acronyms for the non-state actor(s) to retrieve conflict data for
    
    :return: A dictionary with "result" string containing the formatted research data and "citations" list of citation objects
    """
    tool_name = "get_armed_conflict_data_by_non_state_actor"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        # Make sure Neo4j is connected
        global graph
        if graph is None:
            # Try to initialize the connection
            graph = initialize_neo4j(local_testing=True)
            
        # Create research task from parameters
        research_task = f"RULAC conflict data for non-state actor(s): {', '.join(non_state_actors)}"
        
        # Prepare the parameters for the query
        params = {
            "target_non_state_actor_name_and_aliases": non_state_actors,  # Keep the internal parameter name the same for compatibility
            "research_task": research_task
        }

        # Load tool-specific cypher template
        TOOL_PROMPT = tool_cypher_RULAC_conflict_by_NonStateActor.PROMPT

        # DEBUGGING statement
        # Create a debug version of the query with parameters substituted
        debug_query = substitute_params(TOOL_PROMPT, params)
        if logger.getEffectiveLevel() == logging.DEBUG:
                panel = Panel(
                    Markdown(debug_query),
                    border_style="blue",
                    title="[TOOL DEBUGGING] Cypher Prompt dynamically compiled for NEO4J",
                    title_align="left",
                    expand=True,
                )            
                console.print(panel)

        # Execute the query using the graph.query() method
        results = graph.query(TOOL_PROMPT, params)
        if not results:
            # Display "no results" message with tool info
            display_formatted_results(
                "No RULAC conflict data found for the specified non-state actors.",
                title="RULAC Search: No Results",
                tool_name=tool_name,
                tool_params=params
            )
            
            # Print end marker for tool execution, as debug log 
            logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (with empty result)\n" + 
                         "="*50 + "[/bold white]\n")
            
            return format_standard_tool_result(
                content="No RULAC data found.",
                citations=[], # Empty List[Citation]
                tool_name=tool_name,
                tool_params=params
            )

        # Assume the first record contains the required RULAC_research field
        research_result = results[0].get("RULAC_research")

        # Process the result data - formatting content and collecting citations in one step
        formatted_content, citations = process_rulac_data(research_result, research_task)

        # Display formatted results
        display_formatted_results(
            formatted_content, 
            title="RULAC Conflicts Involving Non-State Actors", 
            tool_name=tool_name, 
            tool_params=params, 
            citations=citations,
            showFull=False  # Show truncated content for quicker review
        )

        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        # Return both the formatted result and citations using standardized format
        return format_standard_tool_result(
            content=formatted_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
    except Exception as e:
        error_message = f"Error retrieving RULAC data: {str(e)}"
        
        # Display error message with tool info
        display_formatted_results(
            error_message,
            title="RULAC Search: Error",
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )


@tool
async def get_armed_conflict_data_by_organization(
    organizations: List[str],
    conflict_types: List[str],
) -> RULAC_TOOL_RESULT:
    """
    Retreives armed conflict data from RULAC (Rule of Law in Armed Conflict) by one or more organizations. 
    
    Conflict data returned includes: conflict name, historical conflict overview, applicable international humanitarian law, conflict classification, and a list of state actors and non-state actors to the conflict. 

    This tool retrieves all conflicts involving organization members as a state party to active conflict by default, but can also use an optional filter by conflict classification type. Note: There are only three valid conflict classifications, as defined by RULAC: "International Armed Conflict (IAC)", "Non-International Armed Conflict (NIAC)", "Military Occupation".

    This tool can ONLY retrieve information regarding the following Organizations: "European Union", "African Union", "G7", "BRICS", "NATO", "ASEAN"

    ## Steps
    1. Identify the organization(s) to retrieve conflict data for
    2. Identify any conflict classification filters to apply, if requested. By default, return an empty [] for conflict_types to retrieve all conflicts per organization.

    ## Example Tool Call Parameters
    
    Example question:"What IAC conflicts involve BRICS members?"
    organizations: ["BRICS"]
    conflict_types: ["International Armed Conflict (IAC)"]

    Example question:"What conflicts involve NATO?"
    organizations: ["NATO"]
    conflict_types: []

    :param organizations: List of organization names to retrieve conflict data for
    :param conflict_types: List of conflict classification types to filter by in query
    
    :return: A dictionary with "result" string containing the formatted research data and "citations" list of citation objects
    """
    tool_name = "get_armed_conflict_data_by_organization"

    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")

    # Make sure Neo4j is connected
    global graph
    if graph is None:
        # Try to initialize the connection
        graph = initialize_neo4j(local_testing=True)

    # Create research task from parameters
    research_task = f"RULAC conflict data for organization(s): {', '.join(organizations)}" + (f" with conflict classification ({', '.join(conflict_types)})" if conflict_types else "")
    
    # Load tool-specific cypher template
    TOOL_PROMPT = tool_cypher_RULAC_conflict_by_org.PROMPT
    
    # Prepare the parameters for the query
    params = {
        "target_organization_name": organizations,  # Keep the internal parameter name the same for compatibility
        "target_conflict_types": conflict_types,  # Keep the internal parameter name the same for compatibility
        "research_task": research_task
    }

    # DEBUGGING statement
    # Create a debug version of the query with parameters substituted
    debug_query = substitute_params(TOOL_PROMPT, params)
    if logger.getEffectiveLevel() == logging.DEBUG:
            panel = Panel(
                Markdown(debug_query),
                border_style="blue",
                title="[TOOL DEBUGGING] Cypher Prompt dynamically compiled for NEO4J",
                title_align="left",
                expand=True,
            )            
            console.print(panel)

    try:
        # Execute the query using the graph.query() method
        results = graph.query(TOOL_PROMPT, params)
        if not results:
            # Display "no results" message with tool info
            display_formatted_results(
                "No RULAC conflict data found for the specified organizations.",
                title="RULAC Search: No Results",
                tool_name=tool_name,
                tool_params=params
            )
            
            # Print end marker for tool execution, as debug log
            logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (with empty result)\n" + 
                         "="*50 + "[/bold white]\n")
            
            return format_standard_tool_result(
                content="No RULAC data found.",
                citations=[], # Empty List[Citation]
                tool_name=tool_name,
                tool_params=params
            )

        # Assume the first record contains the required RULAC_research field
        research_result = results[0].get("RULAC_research")

        # Process the result data - formatting content and collecting citations in one step
        formatted_content, citations = process_rulac_data(research_result, research_task)

        # Display formatted results
        display_formatted_results(
            formatted_content, 
            title="RULAC Conflicts Involving Organizations", 
            tool_name=tool_name, 
            tool_params=params, 
            citations=citations,
            showFull=False  # Show full content for this comprehensive report
        )

        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")

        # Return formatted result using standardized format
        return format_standard_tool_result(
            content=formatted_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )

    except Exception as e:
        error_message = f"Error retrieving RULAC data: {str(e)}"
        
        # Display error message with tool info
        display_formatted_results(
            error_message,
            title="RULAC Search: Error",
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )



@tool
async def get_armed_conflict_data_by_region(
    regions: List[str],
    conflict_types: List[str],
) -> RULAC_TOOL_RESULT:
    """
    Retreives conflict data from RULAC (Rule of Law in Armed Conflict) on armed conflicts taking place in specific regions of the world.
    
    Conflict data returned includes: conflict name, historical conflict overview, applicable international humanitarian law, conflict classification, and a list of state actors and non-state actors to the conflict.

    This tool retreives all conflicts in a region by default, but can also use an optional filter by conflict classification type. Note: There are only three valid conflict classifications, as defined by RULAC: "International Armed Conflict (IAC)", "Non-International Armed Conflict (NIAC)", "Military Occupation".

    ## Steps
    1. Identify the region(s) to retrieve conflict data for, using the official regions below
    2. Identify any conflict classification filters to apply, if requested. If there are no conflict classification filters to apply, return an empty [] for conflict_types

    
#### Official Regions
Regions
  ├── Africa
  │   ├── Northern Africa
  │   ├── Sub-Saharan Africa
  │   │   ├── Eastern Africa
  │   │   ├── Middle Africa
  │   │   ├── Southern Africa
  │   │   └── Western Africa
  ├── Americas
  │   │   ├── Northern America
  │   │   ├── Caribbean
  │   │   └── Central America
  │   └── Latin America and the Caribbean
  │       ├── Caribbean
  │       ├── Central America
  │       └── South America
  ├── Antarctica
  ├── Asia
  │   ├── Central Asia
  │   ├── Eastern Asia 
  │   ├── South-Eastern Asia
  │   ├── Southern Asia
  │   └── Western Asia
  ├── Europe
  │   ├── Eastern Europe 
  │   ├── Northern Europe
  │   ├── Southern Europe
  │   └── Western Europe
  └── Oceania


    ## Example Tool Call Parameters
    
    Example question:"How does the number of conflicts taking place in Eastern Africa region compare to those in North Africa region?"
    regions: ["Eastern Africa", "Northern Africa"]
    conflict_types: []

    Example question:"What IAC conflicts are taking place in Europe?"
    regions: ["Europe"]
    conflict_types: ["International Armed Conflict (IAC)"]


    :param regions: List of UN region names to retrieve conflict data for
    :param conflict_types: List of conflict classification types to filter by in query
    :return: A dictionary with "result" string containing the formatted research data and "citations" list of citation objects
    """
    tool_name = "get_armed_conflict_data_by_region"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        # Make sure Neo4j is connected
        global graph
        if graph is None:
            # Try to initialize the connection
            graph = initialize_neo4j(local_testing=True)

        # Create research task from parameters
        research_task = f"RULAC conflict data for region(s): {', '.join(regions)}" + (f" with conflict classification ({', '.join(conflict_types)})" if conflict_types else "")
        
        # Load tool-specific cypher template
        TOOL_PROMPT = tool_cypher_RULAC_conflict_by_Region.PROMPT
        
        # Prepare the parameters for the query
        params = {
            "regions": regions,  # Keep the internal parameter name the same for compatibility
            "target_conflict_types": conflict_types,  # Keep the internal parameter name the same for compatibility
            "research_task": research_task
        }

        # DEBUGGING statement
        # Create a debug version of the query with parameters substituted
        debug_query = substitute_params(TOOL_PROMPT, params)
        if logger.getEffectiveLevel() == logging.DEBUG:
                panel = Panel(
                    Markdown(debug_query),
                    border_style="blue",
                    title="[TOOL DEBUGGING] Cypher Prompt dynamically compiled for NEO4J",
                    title_align="left",
                    expand=True,
                )            
                console.print(panel)

        # Execute the query using the graph.query() method
        results = graph.query(TOOL_PROMPT, params)
        if not results:
            # Display "no results" message with tool info
            display_formatted_results(
                "No RULAC conflict data found for the specified regions.",
                title="RULAC Search: No Results",
                tool_name=tool_name,
                tool_params=params
            )
            
            # Print end marker for tool execution, as debug log
            logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                         f"ENDING TOOL: {tool_name} (with empty result)\n" + 
                         "="*50 + "[/bold white]\n")
            
            return format_standard_tool_result(
                content="No RULAC data found.",
                citations=[], # Empty List[Citation]
                tool_name=tool_name,
                tool_params=params
            )

        # Assume the first record contains the required RULAC_research field
        research_result = results[0].get("RULAC_research")

        # Process the result data - formatting content and collecting citations in one step
        formatted_content, citations = process_rulac_data(research_result, research_task)

        # Display formatted results
        display_formatted_results(
            formatted_content, 
            title="RULAC Conflicts by Region", 
            tool_name=tool_name, 
            tool_params=params, 
            citations=citations,
            showFull=False  # Show full content for this comprehensive report
        )

        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
                
        # Return both the formatted result and citations
        return format_standard_tool_result(
            content=formatted_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
    except Exception as e:
        error_message = f"Error retrieving RULAC data: {str(e)}"
        
        # Display error message with tool info
        display_formatted_results(
            error_message,
            title="RULAC Search: Error",
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )





# TESTING SUITES

# An async event emitter that prints out any events emitted by the tool.
async def event_emitter(event):
    print("Event emitted:", event)
    description = event.get("data", {}).get("description", "No description available")  # Safely extract description
        
    panel = Panel.fit(description, style="black on yellow", border_style="yellow")
        
    # Print nicely formatted box to console
    console.print(panel)

# THESE TOOLS RETURN DIFFERENT DATA STRUCTURES, ie they do not include conflict details but rather a single text string

@tool
async def get_RULAC_conflict_classification_methodology() -> RULAC_TOOL_RESULT:
    """
    Retreives information about RULAC's methodology for classifying armed conflicts according to international humanitarian law.

    Use this tool when the user wants to know how RULAC determines if a situation is an armed conflict or for general information about RULAC's conflict classification methodology.

    If the user wants to know about the specific classification of a conflict, use the get_armed_conflict_data_by_country tool instead.
    This tool is only for general information about RULAC's conflict classification methodology.

    Example question: "How does RULAC classify conflicts?"
    Example question: "What is RULAC's conflict classification methodology?"
    Example question: "How does RULAC distinguish between IAC and NIAC?"
    Example question: "What is the difference between IAC and NIAC?"

    :return: A dictionary with "result" string containing the methodology information and "citations" list of citation objects
    """
    tool_name = "get_RULAC_conflict_classification_methodology"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        # Get content from imported prompt
        methodology_content = baselineClassificationMethodology.PROMPT
        
        # Create research task
        research_task = "RULAC conflict classification methodology"
        
        # Create citations
        citations = [
            create_standard_citation(
                title="RULAC - Classification Methodology",
                url="https://www.rulac.org/classification",
                formatted_content=methodology_content
            )
        ]
        
        # Prepare parameters for the query
        params = {
            "research_task": research_task
        }
        
        # Display formatted results
        display_formatted_results(
            methodology_content, 
            title="RULAC CONFLICT CLASSIFICATION METHODOLOGY", 
            tool_name=tool_name, 
            tool_params=params,
            citations=citations,
            beacon_tool_source="RULAC",
            showFull=False  # Show full methodology content for detailed reference
        )
        
        # Format result
        result = format_standard_tool_result(
            content=methodology_content,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution, as debug log
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return result
        
    except Exception as e:
        error_message = f"Error retrieving RULAC methodology: {str(e)}"
        logger.error(error_message)
        
        # Format error result
        error_result = format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution, as debug log
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return error_result

@tool
async def get_international_law_framework(
    law_focus: str,
) -> RULAC_TOOL_RESULT:
    """
    Returns information about the specified international law framework.
    
    Use this tool when the user wants to know more about international legal frameworks 
    applicable to armed conflicts. The tool supports three specialized areas of law:
    
    - International Humanitarian Law (IHL): The law regulating conduct in armed conflicts
    - International Human Rights Law (IHR): The law protecting human rights
    - International Criminal Law (ICL): The law establishing individual criminal responsibility

    If the user wants to know about a specific law that applies to a specific conflict, 
    use the get_armed_conflict_data_by_country tool instead.
    
    Example question: "What is international humanitarian law?"
    Example question: "Tell me about international human rights law"
    Example question: "What are war crimes under international criminal law?"
    Example question: "How does international humanitarian law differ from human rights law?"

    :param law_focus: Which international law framework to return information about.
                      Must be one of: "International Humanitarian Law (IHL)", 
                      "International Human Rights Law (IHR)", or "International Criminal Law (ICL)"
    
    :return: A dictionary with "result" string containing information about the selected legal framework and "citations" list
    """
    tool_name = "get_international_law_framework"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        # Get the appropriate content based on law_focus parameter
        if law_focus == "International Humanitarian Law (IHL)":
            legal_info = baselineIHLLegalFramework.PROMPT_IHL_LEGAL_FRAMEWORK
            citation_title = "RULAC - International Humanitarian Law Framework"
            citation_url = "https://www.rulac.org/legal-framework/international-humanitarian-law"
            display_title = "INTERNATIONAL HUMANITARIAN LAW LEGAL FRAMEWORK"
        elif law_focus == "International Human Rights Law (IHR)":
            legal_info = baselineIHLLegalFramework.PROMPT_IHR_LEGAL_FRAMEWORK
            citation_title = "RULAC - International Human Rights Law Framework"
            citation_url = "https://www.rulac.org/legal-framework/international-human-rights-law"
            display_title = "INTERNATIONAL HUMAN RIGHTS LAW LEGAL FRAMEWORK"
        elif law_focus == "International Criminal Law (ICL)":
            legal_info = baselineIHLLegalFramework.PROMPT_ICL_LEGAL_FRAMEWORK
            citation_title = "RULAC - International Criminal Law Framework"
            citation_url = "https://www.rulac.org/legal-framework/international-criminal-law"
            display_title = "INTERNATIONAL CRIMINAL LAW LEGAL FRAMEWORK"
        else:
            error_message = f"Invalid law_focus parameter: {law_focus}. Must be one of: 'International Humanitarian Law (IHL)', 'International Human Rights Law (IHR)', or 'International Criminal Law (ICL)'"
            logger.error(error_message)
            return format_standard_tool_result(
                content=error_message,
                citations=[],
                tool_name=tool_name,
                tool_params={"law_focus": law_focus}
            )
        
        # Create research task
        research_task = f"RULAC {law_focus} legal framework"
        
        # Prepare parameters for the query
        params = {
            "research_task": research_task,
            "law_focus": law_focus
        }

        # Add citation for the legal framework information
        citations = [
            create_standard_citation(
                title=citation_title,
                url=citation_url,
                formatted_content=legal_info
            )
        ]
        
        # Display formatted results with a custom title
        display_formatted_results(
            legal_info, 
            title=display_title, 
            tool_name=tool_name, 
            tool_params=params,
            citations=citations,
            showFull=False  # Show full content for detailed reference
        )
                
        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")

        # Format standardized result
        result = format_standard_tool_result(
            content=legal_info,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
        return result
        
    except Exception as e:
        error_message = f"Error retrieving {law_focus} framework data: {str(e)}"
        
        # Format error result
        error_result = format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params={"law_focus": law_focus}
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return error_result

@tool
async def get_information_about_RULAC() -> RULAC_TOOL_RESULT:
    """
    Retrieves general information about the Rule of Law in Armed Conflicts (RULAC) project.

    Use this tool when the user asks for general information about RULAC.

    Example question: "What is RULAC?"
    Example question: "Tell me about the Rule of Law in Armed Conflicts project"
    Example question: "What is the purpose of RULAC?"

    :return: A dictionary with "result" string containing the baseline RULAC information and "citations" list of citation objects
    """
    tool_name = "get_information_about_RULAC"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        baseline_info = baselineRULACinfo.PROMPT
        
        # Create research task
        research_task = "RULAC baseline information"
        
        # Prepare parameters for the query
        params = {
            "research_task": research_task
        }

        # Create citation for the baseline information
        citations = [
            create_standard_citation(
                title="RULAC - About Rule of Law in Armed Conflicts Project",
                url="https://www.rulac.org/about",
                formatted_content=baseline_info
            )
        ]
        
        # Display formatted results with a custom title
        display_formatted_results(
            baseline_info, 
            title="RULAC BASELINE INFORMATION", 
            tool_name=tool_name, 
            tool_params=params,
            citations=citations,
            showFull=False  # Show full content for detailed reference
        )
        
        # Format standardized result
        result = format_standard_tool_result(
            content=baseline_info,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return result
        
    except Exception as e:
        error_message = f"Error retrieving RULAC baseline information: {str(e)}"
        
        # Format error result
        error_result = format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return error_result

@tool
async def get_information_about_Argos() -> RULAC_TOOL_RESULT:
    """
    Retrieves general information about Argos.

    Use this tool when the user asks for general information about Argos, or asks about your purpose, capabilities, or tools.

    Example question: "What is Argos?"
    Example question: "Tell me about the Argos research pipeline"
    Example question: "What is the purpose of Argos?"
    Example question: "What tools does Argos have?"
    Example question: "What is the difference between Argos and RULAC?"
    Example question: "What is your name?"
    Example question: "What can you do?"

    :return: A dictionary with "result" string containing the baseline Argos information and "citations" list of citation objects
    """
    tool_name = "get_information_about_Argos"
    
    # Print start marker for tool execution, as debug log
    logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                 f"STARTING TOOL: {tool_name}\n" + 
                 "="*50 + "[/bold white]\n")
    
    try:
        baseline_info = baselineARGOSinfo.PROMPT
        
        # Create research task
        research_task = "Baseline information about Argos"
        
        # Prepare parameters for the query
        params = {
            "research_task": research_task
        }

        # Create citation for the baseline information
        # citations = [
        #     create_standard_citation(
        #         title="Argos - Advanced Research Pipeline for Armed Conflict Analysis",
        #         url="https://github.com/your-org/argos",
        #         formatted_content=baseline_info
        #     )
        # ]
        
        citations = []
        # Display formatted results with a custom title
        display_formatted_results(
            baseline_info, 
            title="ARGOS BASELINE INFORMATION", 
            tool_name=tool_name, 
            tool_params=params,
            citations=citations,
            showFull=False  # Show full content for detailed reference
        )
        
        # Format standardized result
        result = format_standard_tool_result(
            content=baseline_info,
            citations=citations,
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution before returning
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (success)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return result
        
    except Exception as e:
        error_message = f"Error retrieving Argos baseline information: {str(e)}"
        
        # Format error result
        error_result = format_standard_tool_result(
            content=error_message,
            citations=[],
            tool_name=tool_name,
            tool_params=params
        )
        
        # Print end marker for tool execution on error
        logger.debug(f"\n[bold white]" + "="*50 + "\n" + 
                     f"ENDING TOOL: {tool_name} (with error)\n" + 
                     "="*50 + "[/bold white]\n")
        
        return error_result

def emit_status(message, status_type="info"):
    """
    Emit a status message using console.print.
    
    Args:
        message: The status message to emit
        status_type: The type of status message (info, error, etc.)
    """
    if status_type == "error":
        console.print(Panel(message, style="white on red", border_style="red"))
    elif status_type == "success":
        console.print(Panel(message, style="black on green", border_style="green"))
    else:
        console.print(Panel(message, style="black on yellow", border_style="yellow"))


async def run_tests():
    """
    Run all test functions for RULAC tools using the standardized test approach.
    This centralizes all test configuration in one place.
    """
    console.print(Panel("[bold]STARTING RULAC TOOLS TESTS[/]", style="bold white on green", border_style="green"))
    
    # Test Scenario Definitions
    state_actor_scenarios = [
        {
            "name": "Country: France (IAC Filter)",
            "params": {
                "countries": ["France"],
                "conflict_types": ["International Armed Conflict (IAC)"],
            },
        },
        {
            "name": "Country: USA (No Filter)",
            "params": {
                "countries": ["United States of America"],
                "conflict_types": [],
            },
        },
        {
            "name": "Multiple Countries",
            "params": {
                "countries": ["France", "Russia"],
                "conflict_types": [],
            },
        },
    ]
    
    non_state_actor_scenarios = [
        {
            "name": "Non-State Actor: Hezbollah",
            "params": {
                "non_state_actors": [
                    "Hezbollah", "Hizbollah", "Hizbullah", "Hizballah", "Party of God"
                ],
            },
        },
        {
            "name": "Non-State Actor: ISIS",
            "params": {
                "non_state_actors": [
                    "ISIS", "Islamic State", "Daesh"
                ],
            },
        },
    ]
    
    country_scenarios = [
        {
            "name": "Country: Ukraine (No Filter)",
            "params": {
                "research_query": "Retrieve RULAC conflict taking place in Ukraine",
                "target_country_UN_M49_codes": ["804"],
                "target_conflict_types": [],
            },
        },
    ]
    
    organization_scenarios = [
        {
            "name": "Organization: BRICS (IAC Filter)",
            "params": {
                "organizations": ["BRICS"],
                "conflict_types": ["International Armed Conflict (IAC)"],
            },
        },
        {
            "name": "Organization: NATO (No Filter)",
            "params": {
                "organizations": ["NATO"],
                "conflict_types": [],
            },
        },
        {
            "name": "Multiple Organizations",
            "params": {
                "organizations": ["BRICS", "NATO"],
                "conflict_types": [],
            },
        },
    ]
    
    region_scenarios = [
        {
            "name": "Region: Eastern Africa (No Filters)",
            "params": {
                "regions": ["Eastern Africa"],
                "conflict_types": [],
            },
        },
        {
            "name": "Region: Europe (IAC Filter)",
            "params": {
                "regions": ["Europe"],
                "conflict_types": ["International Armed Conflict (IAC)"],
            },
        },
        {
            "name": "Multiple Regions",
            "params": {
                "regions": ["Eastern Africa", "Northern Africa"],
                "conflict_types": [],
            },
        },
    ]
    
    methodology_scenarios = [
        {
            "name": "Classification Methodology Request",
            "params": {},
        },
    ]
    
    ihl_framework_scenarios = [
        {
            "name": "IHL Framework Request",
            "params": {
                "law_focus": "International Humanitarian Law (IHL)"
            },
        },
        {
            "name": "IHR Framework Request",
            "params": {
                "law_focus": "International Human Rights Law (IHR)"
            },
        },
        {
            "name": "ICL Framework Request",
            "params": {
                "law_focus": "International Criminal Law (ICL)"
            },
        }
    ]
    
    baseline_info_scenarios = [
        {
            "name": "Basic Information Request",
            "params": {},
        },
    ]
    
    argos_info_scenarios = [
        {
            "name": "Argos Information Request",
            "params": {},
        },
    ]
    
    # Run tests based on user configuration
    # Uncomment which tests you want to run
    
    # Neo4j-based tool tests
    # await standardized_tool_test(
    #     get_armed_conflict_data_by_country,
    #     state_actor_scenarios,
    #     "Testing RULAC Country Involvement"
    # )

    # await standardized_tool_test(
    #     get_armed_conflict_data_by_non_state_actor,
    #     non_state_actor_scenarios,
    #     "Testing RULAC Non-State Actor Involvement"
    # )

    # await standardized_tool_test(
    #     get_armed_conflict_data_by_organization,
    #     organization_scenarios,
    #     "Testing RULAC Organization Involvement"
    # )

    # await standardized_tool_test(
    #     get_armed_conflict_data_by_region,
    #     region_scenarios,
    #     "Testing RULAC Region Involvement"
    #     )

    # await standardized_tool_test(
    #     get_RULAC_conflict_classification_methodology,
    #     methodology_scenarios,
    #     "Testing RULAC Conflict Classification Methodology"
    # )

    # await standardized_tool_test(
    #     get_international_law_framework,
    #     ihl_framework_scenarios,
    #     "Testing RULAC International Humanitarian Legal Framework"
    # )

    await standardized_tool_test(
        get_information_about_RULAC,
        baseline_info_scenarios,
        "Testing RULAC Baseline Information"
    )

    await standardized_tool_test(
        get_information_about_Argos,
        argos_info_scenarios,
        "Testing Argos Baseline Information"
    )       
    
    console.print(Panel("[bold]ALL TESTS COMPLETED[/]", style="bold white on green", border_style="green"))


if __name__ == "__main__":
    import asyncio
    
    # Run the async test function
    asyncio.run(run_tests())