"""
description: Argos is an AI assistant specialized in armed conflict analysis, human rights and international humanitarian law.
requirements: coloredlogs==15.0.1, aiolimiter, instructor, groq==0.21.0, langgraph, langchain-groq==0.2.1, langchain-core==0.3.35, langchain-community==0.3.10, pydantic==2.10.3, fastapi==0.115.6, asyncio, langchain-neo4j==0.3.0, requests==2.32.3, langchain-mistralai==0.2.6, rich, openai, mistralai, beautifulsoup4==4.12.3
"""
from typing import AsyncGenerator
from typing import Any, Awaitable, Callable
from langchain_groq import ChatGroq
from groq import Groq
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from fastapi import Request
import asyncio
import os
import json
import re
import requests
import coloredlogs
from langchain_core.tools import tool
import logging
from langchain_core.messages import (
    AIMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
    BaseMessageChunk
)
from langchain_core.messages.utils import convert_to_openai_messages
from langchain_mistralai import ChatMistralAI
# from langchain_ollama import ChatOllama
# from langchain_mistralai.agents import Agents
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
import os
from mistralai import Mistral
from openai import OpenAI
from typing import List, Dict, Optional, Union
from typing import Generator, Iterator
from typing import AsyncGenerator
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, urljoin
import time
import instructor
from instructor import from_groq

# Load Beacon public code files either in mounted volume (when running normally) or just from local files (when running tests)
if os.path.exists("/app/backend/beacon_code"):
    # Ensure that the mounted volume is in sys.path so that the beacon_code package can be found.
    sys.path.insert(0, "/app/backend/beacon_code")
    print("DEBUG: Updated sys.path:", sys.path)

# Load public files from either local files or on server if os path exists
try:
    # load tools / functions
    from tools.RULAC_tools import get_armed_conflict_data_by_country
    from tools.RULAC_tools import get_armed_conflict_data_by_non_state_actor
    from tools.RULAC_tools import get_armed_conflict_data_by_organization
    from tools.RULAC_tools import get_armed_conflict_data_by_region
    from tools.RULAC_tools import get_information_about_RULAC
    from tools.RULAC_tools import get_RULAC_conflict_classification_methodology
    from tools.RULAC_tools import get_international_law_framework
    from tools.RULAC_tools import get_information_about_Argos
    # from tools.WEB_tools import get_website  # Temporarily disabled
    from tools.BRAVE_tools import brave_search  # New Brave Search tool
    from tools.HRW_tools import get_human_rights_research_by_country

    from tools.NEWS_tools import get_combined_news


    # load Final System Prompts for General and Tool Agent
    from prompts.final_prompts import final_argos_base_model_prompt
    from prompts.final_prompts import final_tool_prompt

    # Import our new Router from agents folder
    from agents.router import Router, RouterResponse

except Exception as e:
    print("DEBUG: Error importing public files:", e)
    raise


# // LOGGING //

# Configure logging (should be set to INFO unless DEBUG needed)
logger = logging.getLogger("Argos")
coloredlogs.install(
    logger=logger,
    level="ERROR",
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
)
# Initialize Rich Console
console = Console()

# Debug logging level
print(f"DEBUG - Logger level after initialization: {logger.level} (ERROR={logging.ERROR}, INFO={logging.INFO}, DEBUG={logging.DEBUG})")

# Set logger level explicitly after all imports - will be called when all imports are done
def reset_logger_level(level=logging.ERROR):
    """Helper to ensure logger level is set correctly after all imports"""
    logger.setLevel(level)
    print(f"DEBUG - Logger level after reset: {logger.level}")
    
# Add new debug helpers for API calls
def log_api_request(provider, model, params=None):
    """Log details about an API request"""
    logger.debug(f"API Request to {provider} - Model: {model}")
    if params and logger.isEnabledFor(logging.DEBUG):
        sanitized_params = {k: v for k, v in params.items() if k not in ['messages']}
        if 'messages' in params:
            sanitized_params['message_count'] = len(params['messages'])
        console.print(Panel(
            Pretty(sanitized_params),
            title=f"[bold]{provider} Request Parameters[/bold]",
            border_style="blue",
            expand=False
        ))

def log_api_response_time(provider, model, start_time, status="success"):
    """Log the time taken for an API call"""
    duration = time.time() - start_time
    color = "green" if status == "success" else "red"
    logger.info(f"API Response from {provider} ({model}) - Time: {duration:.2f}s - Status: {status}")
    if duration > 5:
        logger.warning(f"Slow API response from {provider} ({model}): {duration:.2f}s")

# Helper function to log all messages being sent to an LLM
def log_final_messages(messages, title="Messages to LLM"):
    """
    Display all messages being sent to an LLM in a nicely formatted panel.
    
    Args:
        messages (list): List of messages (can be LangChain message objects or dicts with role/content)
        title (str, optional): The title for the panel. Defaults to "Messages to LLM".
    """
    # Create a prettier title with a timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_title = f"[bold magenta]{title}[/] [dim]({timestamp})[/]"
    
    # Format messages for display
    formatted_text = Text()
    
    # Count messages by role for summary
    role_counts = {}
    
    for i, msg in enumerate(messages):
        # Handle different message formats (LangChain objects vs dicts)
        if isinstance(msg, dict):
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            # LangChain message objects
            role = msg.type.upper()
            content = msg.content
        else:
            # Fallback for other object types
            role = type(msg).__name__.upper()
            content = str(msg)
            
        # Update role counts
        role_counts[role] = role_counts.get(role, 0) + 1
        
        # Format the message
        formatted_text.append(f"\n[{i+1}] ", style="bold")
        
        # Color-code by role
        if role == "SYSTEM" or role == "SYSTEMMESSAGE":
            formatted_text.append(f"{role}: ", style="bold red")
            # Truncate long system messages
            if len(content) > 200:
                preview = content[:200].replace('\n', ' ').replace('  ', ' ')
                formatted_text.append(f"{preview}... [truncated, {len(content)} chars]\n")
            else:
                formatted_text.append(f"{content}\n")
        elif role == "USER" or role == "HUMANMESSAGE":
            formatted_text.append(f"{role}: ", style="bold blue")
            formatted_text.append(f"{content}\n")
        elif role == "ASSISTANT" or role == "AIMESSAGE":
            formatted_text.append(f"{role}: ", style="bold green")
            formatted_text.append(f"{content}\n")
        elif role == "TOOL" or role == "TOOLMESSAGE":
            formatted_text.append(f"{role}: ", style="bold yellow")
            # Truncate long tool outputs
            if len(content) > 200:  # Truncate long tool outputs
                preview = content[:200].replace('\n', ' ').replace('  ', ' ')
                formatted_text.append(f"{preview}... [truncated, {len(content)} chars]\n")
            else:
                formatted_text.append(f"{content}\n")
        else:
            formatted_text.append(f"{role}: ", style="bold")
            formatted_text.append(f"{content}\n")
    
    # Create summary of message counts
    summary = " | ".join([f"{role}: {count}" for role, count in role_counts.items()])
    logger.debug(f"Logging {len(messages)} messages: {summary}")
    
    # Add summary to the top
    summary_text = Text(f"Total: {len(messages)} messages ({summary})\n", style="bold underline")
    formatted_text = Text.assemble(summary_text, formatted_text)
    
    # Display in a panel
    panel = Panel(
        formatted_text,
        style="white on black",
        border_style="magenta",
        title=formatted_title,
        title_align="left",
        expand=False,
        width=120  # Limit width for better readability
    )
    console.print(panel)

# // TYPE DEFINITIONS //

class User(BaseModel):
    """Available User data from OPENWEBUI"""
    id: str
    email: str
    name: str
    role: str

class ToolCall(BaseModel):
    """Structured definition of a tool call requested by the LLM"""
    name: str = Field(..., description="The name of the tool to call")
    args: dict = Field(..., description="The arguments to pass to the tool")
    reasoning: str = Field("", description="Explanation of why this tool was selected")

# // HELPER FUNCTIONS //

def load_template_from_path(file_path: str) -> str:
    """
    Load template text from a local file path.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def generate_title(body: dict) -> str:
    """Generate a concise title using Groq LLM based on the user's query"""
    try:
        # Initialize Groq client
        chat_client = Groq(api_key="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")
        
        # Get the user's message
        messages = body.get("messages", [])
        if not messages:
            return json.dumps({"title": "New Chat"})
            
        # Format messages for the LLM
        completion = chat_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": messages[0].get("content", "")}],
            temperature=0.1,
            max_tokens=100,  # Keep it concise
            stream=False
        )
        
        # Extract the title from the response
        response = completion.choices[0].message.content.strip()
        
        # Try to parse as JSON if it's already in JSON format
        try:
            json_response = json.loads(response)
            if isinstance(json_response, dict) and "title" in json_response:
                return json.dumps(json_response)
        except json.JSONDecodeError:
            pass
            
        # If not JSON, clean the response and format it as JSON
        # Remove any quotes or special characters
        title = response.replace('"', '').replace("'", "").strip()
        # Limit length and wrap in JSON format
        title = title[:50]  # Limit length
        
        return json.dumps({"title": title})
        
    except Exception as e:
        print(f"Error generating title: {e}")
        return json.dumps({"title": "New Chat"})

# // PIPELINE //

class Pipe:

    # Setup user-configurable Valves providing API keys and access
    class Valves(BaseModel):
        MODEL_ID: str = Field(default="argos", description="Model ID for the Argos project")
        groq_api_key: str = Field("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", description="API key for Groq")
        mistral_api_key: str = Field("9hblEwepQtzvyY9y4incc3yvApk4ArJO", description="API key for Mistral")
        deepseek_api_key: str = Field("sk-28cf4f690b704c76b3f3c6622d7b87cd", description="API key for Deepseek")
        
        # Web search tool parameters
        searxng_url: str = Field("http://localhost:8081/search", description="SearXNG API URL")
        ignored_websites: str = Field("", description="Comma-separated list of websites to ignore in search results")
        page_content_words_limit: int = Field(5000, description="Limit words content for each page")

        

    # Initialize pipeline (ie. once at start) to define the neo4j URL and the LLMs to use
    def __init__(self, local_testing: bool = False):

        self.name = "Argos"

        # Reset logger level explicitly after all imports. Important: this is ultimately where the logger level is set.
        # When running locally, set the logger level to INFO to see more detailed output. When running on the server, set it to ERROR to reduce verbosity.
        reset_logger_level(logging.ERROR if not local_testing else logging.INFO)

        self.valves = self.Valves()
        self.local_testing = local_testing  # Set local testing flag
        self.global_unique_citations_retreived = set()
        self.global_citation_count = 0  # Reset the citation count at the start of each pipe run
        self.event_emitter = None  # Will be set in pipe() method
        self.is_first_tool_status_update = True # Flag for delayed status updates
        self.tool_status_lock = asyncio.Lock() # Lock for handling parallel status updates
        
        # Not sure if i need this, but openwebui tools docs say to set citation to False if you want to customise the citation event ... wont hurt to keep just in case
        # self.citation = False

        # For local testing, create a mock event emitter that displays events in the console
        if self.local_testing:
            self.mock_event_emitter = self.create_mock_event_emitter()
        
        # // Initialize all LLMs using API key and models //

        # 1. Router LLM (in order of pref)
        # Initialize the router directly - it now creates its own groq client with instructor
        self.router = Router()
        # Set the API key from valves
        self.router.groq_api_key = self.valves.groq_api_key

        # 2. General LLM (in order of pref)
        self.general_model = ChatGroq(groq_api_key=self.valves.groq_api_key, model="llama-3.3-70b-versatile", temperature=0, streaming=True) # Basic start w fast and general intellgent llama3 70B, TO DO: switch to Mistral


        # 3. Tool-Use LLM (in order of pref) - Must be a LLM that features tool use (llama3, etc.)
        # Initialize the Groq client with instructor for structured output
        groq_client = Groq(api_key=self.valves.groq_api_key)
        # Set up instructor client with debug mode

        # instructor.patch() is not needed - from_groq() already patches the client
        self.structured_client = from_groq(groq_client, mode=instructor.Mode.JSON)
        self.tool_model_name = "qwen/qwen3-32b"
        self.tool_temperature = 0.6
        
        # Keep the regular tool model for backward compatibility
        self.tool_model = ChatGroq(groq_api_key=self.valves.groq_api_key, model=self.tool_model_name, temperature=self.tool_temperature, model_kwargs={"reasoning_format": "parsed"})

        # Define tools for both regular ChatGroq and instructor
        self.tools = [
            # RULAC tools
            get_armed_conflict_data_by_country,
            get_armed_conflict_data_by_non_state_actor,
            get_armed_conflict_data_by_organization,
            get_armed_conflict_data_by_region,
            get_information_about_RULAC,
            get_RULAC_conflict_classification_methodology,
            get_international_law_framework,
            get_information_about_Argos,
            # Web search tools
            brave_search,  # Added Brave Search tool
            # get_website,  # Temporarily disabled
            # Human Rights tools
            get_human_rights_research_by_country,
            # News tools
            get_combined_news
        ]
        
        # Bind tools to the regular LangChain tool model
        self.tool_model_with_tools = self.tool_model.bind_tools(self.tools)
        
        # Convert LangChain tools to OpenAI-compatible format for instructor
        # This will be used in handle_tool_query method
        
        # Add default tool-friendly names for UI status updates, they are later updated to the friendly names in the handle_tool_query method
        self.tool_friendly_names = {
            "get_armed_conflict_data_by_country": "Researching state actor involvement in armed conflicts",
            "get_armed_conflict_data_by_non_state_actor": "Researching non-state actor involvement in armed conflicts",
            "get_armed_conflict_data_by_organization": "Researching organizational involvement in armed conflicts",
            "get_armed_conflict_data_by_region": "Researching regional involvement in armed conflicts",
            "get_information_about_RULAC": "Retrieving info about RULAC",
            "get_RULAC_conflict_classification_methodology": "Analyzing conflict classification methodology",
            "get_international_law_framework": "Analyzing international law framework",
            "get_information_about_Argos": "Retrieving info about Argos",
            "get_human_rights_research_by_country": "Analyzing human rights situation",
            "get_combined_news": "Analyzing latest news and developments",
            "brave_search": "Searching the web for info"
        }
        
    def create_mock_event_emitter(self):
        """Creates a mock event emitter for local testing that displays events in the console

        The event emitter expects events in the following format:
        For citations:
        {
            "type": "citation",
            "data": {
                "document": [str],  # List of document content strings
                "metadata": [{      # List of metadata dicts
                    "date_accessed": str,  # ISO format datetime
                    "source": str   # Title/name of source
                }],
                "source": {
                    "name": str,    # URL or source name
                    "url": str      # Full URL to source
                }
            }
        }
        
        For status updates:
        {
            "type": "status", 
            "data": {
                "description": str,  # Status message to display
                "done": bool        # Whether this is the final status
            }
        }

        """
        async def mock_event_emitter(event):
            event_type = event.get("type", "unknown")
            if event_type == "status":
                description = event.get("data", {}).get("description", "No description available")
                panel = Panel.fit(description, style="black on yellow", border_style="yellow")
                console.print(panel)
            # elif event_type == "citation":
            #     # Print the citation event, but only if debug logging is enabled
            #     # if logger.isEnabledFor(logging.DEBUG):
            #     #     logger.debug(f"Citation event received: {event}")
            #     data = event.get("data", {})
            #     source = data.get("source", {})
            #     source_url = source.get("url", "No URL")
            #     metadata = data.get("metadata", [])
                
            #     # Get the title from the metadata - metadata is a list of dictionaries
            #     displayed_source_title = metadata[0].get("source", "Unknown Source") if metadata else "Unknown Source"
            #     # Get document content (first item only for display purposes)
            #     documents = data.get("document", [])
            #     document_preview = documents[0][:200] + "..." if documents and len(documents[0]) > 200 else "No content"
                
            #     # Format the URL for display purposes
            #     parsed_url = urlparse(source_url)
            #     display_url = f"{parsed_url.netloc}{parsed_url.path}"

            #     # Create a citation panel with more information
            #     citation_text = Text()
            #     citation_text.append(f"UI Citation: {displayed_source_title}\n", style="bold")
            #     citation_text.append(f"{display_url}\n", style="underline blue")
            #     citation_text.append(f"Preview: {document_preview}", style="italic")
                

            #     panel = Panel(
            #         citation_text,
            #         style="white on green",
            #         border_style="green", 
            #         title="[CITATION]",
            #         title_align="left"
            #     )
            #     console.print(panel)
        return mock_event_emitter
        
    async def emit_event(self, event):
        """Emit an event using the appropriate event emitter"""
        if self.event_emitter:
            await self.event_emitter(event)
        elif self.local_testing and self.mock_event_emitter:
            await self.mock_event_emitter(event)
            
        
    # Main execution logic that starts and ends full pipeline, messages are sent as 'body' input from the OPENWEBUI app and/or through local testing
    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __request__: Request,
        __event_emitter__=None,
        local_testing: bool = False,
        __task__: str = None
    ) -> Union[str, Generator, Iterator, AsyncGenerator]:
        """
        Main orchestration function that processes user requests and returns AI responses.
        
        This function serves as the central pipeline that:
        1. Analyzes the user's request intent
        2. Performs research with appropriate tools
        3. Generates and streams a response
        4. Tracks and displays citation information
        
        Args:
            body: Dictionary containing conversation messages
            __user__: User information from OpenWebUI
            __request__: FastAPI request object
            __event_emitter__: Function for sending UI updates
            local_testing: Whether running in local test mode
            __task__: Task to be performed, currently only "title_generation" is supported
            
        Returns:
            Streaming response generator that yields tokens to the user
        """
# This pipe is the main pipeline for the Argos project, it is used to process user requests and return AI responses.
# Afterwards, it also used to generate titles for the chat history

# If the body contains a request to generate a title, the pipe will return a title
# Otherwise, it will return a streaming response

        # print(f"REQUEST: {__request__}")
# output the body for debugging purposes
        # print(f"TASK: {__task__}")
        # print("BODY:", body)
# example of body with title generation request
# BODY: {'model': 'argos_agent_v1_mar_2025', 'messages': [{'role': 'user', 'content': 'Here is the query:\nWhat is the human rights situation in Somalia?\n\nCreate a concise, 3-5 word phrase as a title for the previous query. Avoid quotation marks or special formatting. RESPOND ONLY WITH THE TITLE TEXT.\n\nExamples of titles:\nUkraine Conflict Classification\nUganda Press Freedom\nRacial Justice in USA\nEU Judicial Reform\nLGBTQ+ Rights in China'}], 'stream': False, 'max_completion_tokens': 1000}


        # # check if the body contains a request to generate a title, as they always start with "Here is the query:"  
        # if "Here is the query:" in body.get("messages", [{}])[0].get("content", ""):
        #     print("Title Generation Method 1: Using 'in' operator")
        #     # call the generate_title function
        #     title = generate_title(body)
        #     print(f"\nGenerated Title: {title}")
        #     # return the title and exit the pipeline immediately
        #     return title

        # check if task is title generation
        if __task__ == "title_generation":
            if logger.isEnabledFor(logging.INFO):
                print("Title Generation Method detected: Using task")
            # call the generate_title function
            title = generate_title(body)
            if logger.isEnabledFor(logging.INFO):
                print(f"\nGenerated Title: {title}")
            # return the title and exit the pipeline immediately
            return title
        else:
            # print("Title Generation Method not detected: Continuing with pipeline")
            pass

        # return "Test Output"




        # Convert __user__ to User type in OpenWebUI
        user = User(**__user__)

        # Save the event emitter for use throughout the pipe execution
        self.event_emitter = __event_emitter__
        
        # If no event emitter is provided, use the mock event emitter for local testing
        if not self.event_emitter:
            self.event_emitter = self.create_mock_event_emitter()

        # Reset citation tracking variables at start of new pipe run
        self.global_unique_citations_retreived = set()
        self.global_citation_count = 0

        # Print clear start marker for pipeline execution
        # Only print if logging level is INFO or below
        if logger.isEnabledFor(logging.INFO):
            console.print("\n[bold green]" + "="*50 + "\n" + 
                        "STARTING NEW ARGOS PIPELINE EXECUTION\n" + 
                        "="*50 + "[/bold green]\n")

        # Register end marker to be printed at end of execution
        def cleanup():
            if logger.isEnabledFor(logging.INFO):
                console.print("\n[bold green]" + "="*50 + "\n" +
                             "END OF ARGOS PIPELINE EXECUTION\n" + 
                             "="*50 + "[/bold green]\n")
            
        # Register cleanup to run at end of pipe() function
        try:
            import atexit
            atexit.register(cleanup)
        except Exception as e:
            logger.debug(f"Could not register cleanup: {e}")

        # Extract messages from body input
        messages = body.get("messages", [])

        # Remove any system message from the conversation, for now, as OpenWEBUI adds the date in a system message
        # In the future, we can use the system message to provide context to the router, like USER data and history 
        messages = [msg for msg in messages if msg.get("role") != "system"]



        # Execute research tools and get their outputs - directly without router
        tool_outputs = await self.handle_tool_query(messages)
        logger.debug(f"Received {len(tool_outputs)} tool outputs from handle_tool_query")
        
        # Generate final response using tool outputs and original messages
        result = self.handle_tool_query_final_response(tool_outputs, messages)
        
        # Create status message showing citation count for display in the UI
        unique_citation_count = len(self.global_unique_citations_retreived)
        logger.debug(f"Total unique citations: {unique_citation_count}")

        if unique_citation_count:
            eventMessageUI = f"🌐 " + f" Cross-referenced w {unique_citation_count} source{'s' if unique_citation_count != 1 else ''}"
        else:
            eventMessageUI = " "

        # Send final status update to UI
        if eventMessageUI:
            await self.emit_event(
                {
                    "type": "status",
                    "data": {
                        "description": eventMessageUI,
                        "done": True, # This is a final status event
                    },
                }
            )
            
        # Return streaming response generator to OpenWebUI
        return result

    def handle_general_query(self, conversation_messages: list[dict]) -> Generator[str, None, None]:
        """
        Handles general queries that don't require research tools.
        
        This function is used when the router determines that the user's query
        can be answered directly without utilizing specialized research tools.
        It formats messages with a system prompt and streams a response from
        the general model.
        
        Args:
            conversation_messages: List of conversation messages from the user
            
        Returns:
            Generator that yields streaming tokens as they are produced
        """
        # Debug shape of conversation messages
        # logger.debug(f"Actual Conversation Messages passed in: {conversation_messages}")

        # STEP 1: Set up the system prompt with general Argos capabilities
        FINAL_SYSTEM_PROMPT = final_argos_base_model_prompt.PROMPT

        # Add current date/time for temporal context
        currentDateTime = datetime.now(ZoneInfo("Europe/Paris")).strftime("%B %d, %Y %I:%M %p")

        # Create a PromptTemplate and render it with variables
        FINAL_PROMPT = PromptTemplate(
                input_variables=["currentDateTime"],
                template=FINAL_SYSTEM_PROMPT,
            )

        rendered_prompt = FINAL_PROMPT.format(
                currentDateTime=currentDateTime,
            )

        # STEP 2: Prepare messages array starting with system prompt
        system_argos_and_cleaned_conversation_messages = [
            SystemMessage(content=rendered_prompt),
        ]

        # STEP 3: Convert conversation messages to LangChain format
        for msg in conversation_messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            if role == "user":
                system_argos_and_cleaned_conversation_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                system_argos_and_cleaned_conversation_messages.append(AIMessage(content=content))
            elif role == "system":
                # In case system messages are passed in the conversation
                system_argos_and_cleaned_conversation_messages.append(SystemMessage(content=content))
            else:
                # Skip unrecognized roles
                logger.debug(f"Unrecognized role '{role}' in message; skipping.")

        # Log final messages for debugging
        log_final_messages(system_argos_and_cleaned_conversation_messages, "Argos Base Agent Complete Messages")

        logger.debug("Inside general query final response; starting synchronous streaming...")

        # STEP 4: Stream response from the general model
        try:
            # Get streaming generator from the general model
            stream = self.general_model.stream(system_argos_and_cleaned_conversation_messages, stop=None)
            for i, chunk in enumerate(stream):
                if hasattr(chunk, "content"):
                    yield chunk.content
                else:
                    logger.debug(f"Chunk {i} has no 'content' attribute.")
            logger.debug("Finished processing all chunks.")
        except Exception as e:
            logger.error(f"Streaming invocation failed: {e}")
            yield f"Error: {e}"


    async def handle_tool_query(self, messages: list[dict]) -> list[dict]:
        """
        Research orchestration function that selects and executes appropriate research tools.
        
        This function:
        1. Constructs prompts for the tool-using LLM using the conversation messages
        2. Gets tool selection decisions from the LLM using structured output
        3. Executes selected research tools (RULAC, HRW, etc.)
        4. Processes and emits citation information to the UI
        5. Collects all tool outputs for final response generation
        
        Args:
            messages: The full conversation messages from the user
            
        Returns:
            List of dictionaries containing tool outputs with metadata
        """

        if logger.isEnabledFor(logging.INFO):
            console.print("\n[bold yellow]" + "="*50 + "\n" +
                         "START OF TOOL USE AGENT\n" + 
                         "="*50 + "[/bold yellow]\n")


        # Send initial status update to UI
        await self.emit_event(
            {
                "type": "status",
                "data": {
                    "description": "Identifying research tools",
                    "done": False,
                },
            }
        )

        # Initialize data structures for tool processing
        tool_outputs = []  # List to store tool outputs
        
        # Extract the latest user query (last user message in conversation)
        latest_user_query = ""
        conversation_context = ""
        
        # Build conversation context and get the latest user query
        previous_messages = []
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "user":
                latest_user_query = content
            
            # Add to previous messages except the last user message
            if role in ["user", "assistant"]:
                previous_messages.append({"role": role, "content": content})
        
        # Remove the last user message from previous_messages
        if previous_messages and previous_messages[-1].get("role") == "user":
            previous_messages.pop()
        
        # Format conversation context
        if previous_messages:
            for msg in previous_messages:
                role_display = "User" if msg["role"] == "user" else "Assistant"
                conversation_context += f"\n\n**{role_display}**: {msg['content']}"
        
        # Debug output for extracted query and context
        logger.debug(f"Extracted latest user query: {latest_user_query}")
        logger.debug(f"Built conversation context with {len(previous_messages)} messages")
        
        # Prepare the system prompt for the tool-using LLM
        current_date = datetime.now().strftime("%B %d, %Y") # Get current date
        system_message_content = (
            f"""You are a helpful expert in human rights, armed conflict and international humanitarian law named "Argos". 
            You answer questions and complete tasks about human rights, conflict and international humanitarian law by using tools that provide you with research.
            Today's date is {current_date}.

            AVAILABLE TOOLS:

            1. RULAC (Rule of Law in Armed Conflicts) Tools:
               Use these tools to get detailed information about armed conflicts and their legal classification.

               a) State Actor Conflicts:
                  - Tool: get_armed_conflict_data_by_country
                  - Use when: You need information about conflicts involving specific countries
                  - Parameters: 
                    * countries: List of country names
                    * conflict_types: Required list, use empty list [] to get all types or specify from ["International Armed Conflict (IAC)", "Non-International Armed Conflict (NIAC)", "Military Occupation"]

               b) Non-State Actor Conflicts:
                  - Tool: get_armed_conflict_data_by_non_state_actor
                  - Use when: You need information about conflicts involving non-state actors
                  - Parameters:
                    * non_state_actors: List of actor names/aliases

               c) Regional Conflicts:
                  - Tool: get_armed_conflict_data_by_region
                  - Use when: You need information about conflicts in specific regions
                  - Official regions are:
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

                  - Parameters:
                    * regions: List of region names (e.g., "Eastern Africa", "Europe")
                    * conflict_types: Optional list of conflict types

               d) Organization Conflicts:
                  - Tool: get_armed_conflict_data_by_organization
                  - Use when: You need information about conflicts involving specific organizations
                  - Parameters:
                    * organizations: List of organization names (e.g., "NATO", "BRICS")
                    * conflict_types: Optional list of conflict types

               e) General RULAC Information:
                  - Tool: get_information_about_RULAC
                  - Use when: You need general information about the RULAC project
                  - No parameters required

               f) Conflict Classification:
                  - Tool: get_RULAC_conflict_classification_methodology
                  - Use when: You need information about how RULAC classifies conflicts
                  - No parameters required


               g) International Law Framework:
                  - Tool: get_international_law_framework
                  - Use when: You need information about international legal frameworks (IHL, IHR, ICL)
                  - Parameters:
                    * law_focus: Must be one of: "International Humanitarian Law (IHL)", "International Human Rights Law (IHR)", or "International Criminal Law (ICL)"


            2. Human Rights Tools:
               Use these tools to get information about human rights situations.

               a) HRW Reports:
                  - Tool: get_human_rights_research_by_country
                  - Use when: You need the latest Human Rights Watch report for a country
                  - Parameters:
                    * country: The country name
                  - Note: Use this tool whenever a country is mentioned, in addition to other relevant tools

            3. Web Search Tools:
               Use these tools to get current information and answers to factual questions.

               a) Brave Search:
                  - Tool: brave_search
                  - Use when: You need to search for factual information or get summarized answers to questions
                  - Parameters:
                    * query: Your search query. When using this tool, you should break down complex queries into separate focused searches
                  - Note: This tool is useful for getting current information about topics not covered by RULAC or HRW
                  - Note: When using this tool, you should break down complex queries into separate focused searches, and use the tool multiple times if needed

            4. News Tools:
               Use these tools to get the latest news on relevant topics.
               
               a) News Search:
                  - Tool: get_combined_news
                  - Use when: You need the latest news and developments about a specific topic, country, conflict, or event
                  - Parameters:
                    * search_query: Your news search query, which should include keywords only. do not include the word "news" or "latest", only the topic keywords
                  - Note: Use this tool for up-to-date information about recent developments

            5. Argos Tools:
               Use these tools to get information about Argos.

               a) Argos Information:
                  - Tool: get_information_about_Argos
                  - Use when: You need information about Argos, or ask about your purpose, capabilities, or tools
                  - No parameters required
                  
            IMPORTANT NOTES:
            - You can use multiple tools in a single response
            - Prioritize using the RULAC tools for conflict information
            - For RULAC tools, use empty lists [] for optional parameters to get all results
            - Always consider using get_human_rights_research_by_country when countries are mentioned
            - Use brave_search at least once in your response, unless the user is asking about Argos or your purpose
            - If you use get_RULAC_conflict_classification_methodology, you must also use get_armed_conflict_data_by_country or get_armed_conflict_data_by_non_state_actor
            - If the request involves current events or situations that may be changing rapidly, use the get_combined_news tool to fetch the latest information
            
            For each tool you decide to use, provide output in this format:
            {{
              "tools": [
                {{
                  "name": "tool_name",
                  "args": {{"param1": "value1", "param2": "value2"}},
                  "reasoning": "explanation of why you're using this tool"
                }},
                // other tools...
              ]
            }}
            """
        )

        # Add conversation context to system message if available
        prompt_content = system_message_content
        if conversation_context:
            prompt_content += f"\n\nHere is our conversation context:\n{conversation_context}\n\n"
        
        # Add the latest user query
        prompt_content += f"\n\nUser question: {latest_user_query}"
        prompt_content += """

Please analyze this request and identify the specific tools needed to answer it. Your response must be a valid JSON object with this structure:

{{
  "tools": [
    {{
      "name": "[tool name]",
      "args": {{
        "[parameter name]": "[parameter value]",
        ...
      }},
      "reasoning": "[explanation for why this tool is needed]"
    }},
    ...
  ]
}}

Available tool names are:
- get_armed_conflict_data_by_country
- get_armed_conflict_data_by_non_state_actor
- get_armed_conflict_data_by_organization
- get_armed_conflict_data_by_region
- get_information_about_RULAC
- get_RULAC_conflict_classification_methodology
- get_international_law_framework
- get_information_about_Argos
- brave_search
- get_human_rights_research_by_country
- get_combined_news

Examples of proper tool calls:

1. Example for "What conflicts are happening in Ukraine?":
{{
  "tools": [
    {{
      "name": "get_armed_conflict_data_by_country",
      "args": {{
        "countries": ["Ukraine"],
        "conflict_types": []
      }}
      "reasoning": "Need to find information about conflicts in Ukraine"
    }},
    {{
      "name": "get_human_rights_research_by_country",
      "args": {{
        "country": "Ukraine"
      }}
      "reasoning": "Need human rights information for Ukraine"
    }},
    {{
      "name": "brave_search",
      "args": {{
        "query": "What conflicts are taking place in Ukraine?"
      }}
      "reasoning": "Required to provide broader context via web search"
    }}
  ]
}}

2. Example for "What is the current human rights situation in Somalia?":
{{
  "tools": [
    {{
      "name": "get_human_rights_research_by_country",
      "args": {{
        "country": "Somalia"
      }},
      "reasoning": "Need human rights information for Somalia"
    }},
    {{
      "name": "get_combined_news",
      "args": {{
        "search_query": "Somalia human rights violations"
      }},
      "reasoning": "Need latest news and developments about human rights in Somalia"
    }},
    {{
      "name": "brave_search",
      "args": {{
        "query": "What is the human rights situation in Somalia?"
      }}
      "reasoning": "Required to provide additional broader context via web search"
    }}
  ]
}}

3. Example for "What is your name?":
{{
  "tools": [
    {{
      "name": "get_information_about_Argos",
      "args": {{    
      }},
      "reasoning": "Need information about Argos"
    }}
  ]
}}

Return only valid JSON without any other text. Be concise.
"""

        # Create messages for the API call - we'll use the raw Groq client instead of instructor for debugging
        # reasoning models, like groq qwen, expect a user message, not a system message
        structured_messages = [
            {"role": "user", "content": prompt_content}
        ]

        # Log messages being sent to the tool model for debugging, but only if the debug level is set to DEBUG
        if logger.getEffectiveLevel() == logging.DEBUG:
            log_final_messages(structured_messages, "Structured Prompt for Tool Selection")

        try:
            # Get tool selection decisions from the LLM using direct Groq client instead of instructor
            model_name = self.tool_model_name
            log_api_request("Tool Model", model_name, {
                "message_count": len(structured_messages),
                "prompt_tokens_estimate": len(prompt_content) // 4
            })
            
            start_time = time.time()
            logger.info(f"Invoking Tool Selection LLM ({model_name})")
            
            # Initialize raw Groq client for debugging
            direct_client = Groq(api_key=self.valves.groq_api_key)
            
            # Add retry logic for 503 errors
            max_retries = 3
            retry_count = 0
            backoff_time = 1  # Initial backoff in seconds
            
            while retry_count <= max_retries:
                try:
                    # Debug: Try with direct Groq client first
                    logger.debug("Using direct Groq client for debugging")
                    
                    # Add retry logic for 503 errors
                    max_retries = 3
                    retry_count = 0
                    backoff_time = 1  # Initial backoff in seconds
                    
                    while retry_count <= max_retries:
                        try:
                            completion = direct_client.chat.completions.create(
                                model=model_name,
                                messages=structured_messages,
                                temperature=self.tool_temperature,
                                response_format={"type": "json_object"}
                            )
                            
                            log_api_response_time("Tool Model", model_name, start_time)
                            
                            # Extract and parse JSON response
                            json_response = completion.choices[0].message.content
                            logger.debug(f"Raw JSON response: {json_response}")
                            
                            # Print raw API response details (more verbose)
                            if logger.getEffectiveLevel() == logging.DEBUG:
                                console.print(Panel(
                                    Pretty(completion.model_dump()),
                                    title="Debug: Raw Groq API Response",
                                    border_style="magenta",
                                    expand=False
                                ))
                            
                            # Successfully got a response, break out of retry loop
                            break
                            
                        except Exception as retry_e:
                            retry_count += 1
                            error_type = type(retry_e).__name__
                            error_details = str(retry_e)
                            
                            # Check if this is a 503 error
                            is_503_error = False
                            if error_type == "InternalServerError" and "503" in str(error_details):
                                is_503_error = True
                            
                            # Log detailed error information
                            logger.error(f"Tool Model API Error ({error_type}): {error_details}")
                            
                            # If it's a 503 error and we have retries left, retry after backoff
                            if is_503_error and retry_count <= max_retries:
                                wait_time = backoff_time * (2 ** (retry_count - 1))
                                logger.warning(f"Got 503 error, retrying in {wait_time}s (attempt {retry_count}/{max_retries})")
                                # Wait before retry with exponential backoff
                                time.sleep(wait_time)
                            else:
                                # For non-503 errors or if we've used all retries, re-raise to be caught by outer try/except
                                raise retry_e
                    
                    try:
                        parsed_response = json.loads(json_response)
                        logger.debug(f"Parsed response: {json.dumps(parsed_response, indent=2)}")
                        
                        # Debug panel for full response structure
                        if logger.getEffectiveLevel() == logging.DEBUG:
                            console.print(Panel(
                                Pretty(parsed_response),
                                title="Debug: Full Parsed Response",
                                border_style="green"
                            ))
                        
                        # Extract tool calls from the parsed response
                        tool_calls = []
                        if "tools" in parsed_response and isinstance(parsed_response["tools"], list):
                            for i, tool_info in enumerate(parsed_response["tools"]):
                                if "name" in tool_info and "args" in tool_info:
                                    tool_calls.append({
                                        "id": f"tool_{i}",
                                        "name": tool_info["name"],
                                        "args": tool_info["args"],
                                        "reasoning": tool_info.get("reasoning", "No reasoning provided")
                                    })
                        else:
                            logger.warning(f"Unexpected response structure. No 'tools' array found.")
                            # Try to extract any tool-like information from the response
                            if isinstance(parsed_response, dict):
                                for key, value in parsed_response.items():
                                    logger.debug(f"Checking field: {key} = {value}")
                                
                                # Try to find any field that looks like it might contain tools
                                potential_tool_fields = []
                                for key, value in parsed_response.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        potential_tool_fields.append((key, value))
                                
                                if potential_tool_fields:
                                    logger.info(f"Found potential tool fields: {[f[0] for f in potential_tool_fields]}")
                                    # Use the first list field as potential tools
                                    field_name, field_value = potential_tool_fields[0]
                                    logger.info(f"Using '{field_name}' as tools array")
                                    
                                    for i, item in enumerate(field_value):
                                        if isinstance(item, dict):
                                            # Check if this looks like a tool definition
                                            if "name" in item or "tool" in item:
                                                tool_name = item.get("name") or item.get("tool")
                                                # Extract args if available or default to empty dict
                                                args = {}
                                                for arg_key in ["args", "arguments", "parameters"]:
                                                    if arg_key in item and isinstance(item[arg_key], dict):
                                                        args = item[arg_key]
                                                        break
                                                
                                                reasoning = "Extracted from non-standard response"
                                                for reason_key in ["reasoning", "reason", "description", "explanation"]:
                                                    if reason_key in item and isinstance(item[reason_key], str):
                                                        reasoning = item[reason_key]
                                                        break
                                                
                                                tool_calls.append({
                                                    "id": f"extracted_tool_{i}",
                                                    "name": tool_name,
                                                    "args": args,
                                                    "reasoning": reasoning
                                                })
                                    
                                    if tool_calls:
                                        logger.info(f"Successfully extracted {len(tool_calls)} tools from non-standard response")
                                    else:
                                        # No valid tools found, use fallback
                                        logger.warning("No valid tools could be extracted, using fallback")
                                        tool_calls = [{
                                            "id": "fallback_tool",
                                            "name": "get_information_about_Argos",
                                            "args": {},
                                            "reasoning": "Non-standard response format, fallback to general information"
                                        }]
                                else:
                                    # No potential tool fields found, use fallback
                                    logger.warning("No potential tool fields found, using fallback")
                                    tool_calls = [{
                                        "id": "fallback_tool",
                                        "name": "get_information_about_Argos",
                                        "args": {},
                                        "reasoning": "Non-standard response format, fallback to general information"
                                    }]
                    except json.JSONDecodeError as json_e:
                        logger.error(f"Failed to parse JSON: {json_e}")
                        logger.debug(f"Problematic JSON string: {json_response}")
                        # Fallback: try to extract tool names with regex
                        tool_regex = r'"name":\s*"([^"]+)"'
                        tool_matches = re.findall(tool_regex, json_response)
                        logger.debug(f"Found tool names with regex: {tool_matches}")
                        
                        # Create fallback tool call
                        tool_calls = [{
                            "id": "fallback_tool",
                            "name": "get_information_about_Argos",
                            "args": {},
                            "reasoning": "JSON parsing error, fallback to general information"
                        }]
                    
                    # Successfully processed the response, break out of retry loop
                    break
                    
                except Exception as tool_e:
                    retry_count += 1
                    log_api_response_time("Tool Model", model_name, start_time, status="error")
                    error_type = type(tool_e).__name__
                    error_details = str(tool_e)
                    
                    # Check if this is a 503 error that we should retry
                    is_503_error = False
                    if error_type == "InternalServerError" and "503" in str(error_details):
                        is_503_error = True
                    
                    # Log detailed error information
                    logger.error(f"Tool Model API Error ({error_type}): {error_details}")
                    
                    # Create a detailed error panel for inspection
                    error_panel = Panel(
                        f"Error Type: {error_type}\nDetails: {error_details}",
                        title="Tool Model LLM API Error",
                        border_style="red",
                        expand=False
                    )
                    console.print(error_panel)
                    
                    # For 503 errors, retry if we haven't exceeded max retries
                    if is_503_error and retry_count <= max_retries:
                        wait_time = backoff_time * (2 ** (retry_count - 1))
                        logger.warning(f"Got 503 error, retrying in {wait_time}s (attempt {retry_count}/{max_retries})")
                        # Wait before retry with exponential backoff
                        time.sleep(wait_time)
                        continue
                    
                    # If we've used all retries or it's not a 503 error, use the fallback
                    if retry_count > max_retries:
                        logger.warning(f"Max retries ({max_retries}) exceeded, using fallback tool")
                    elif not is_503_error:
                        logger.warning(f"Non-503 error occurred, using fallback tool")
                    
                    # Fallback to basic tool call for get_information_about_Argos
                    tool_calls = [{
                        "id": "fallback_tool",
                        "name": "get_information_about_Argos",
                        "args": {},
                        "reasoning": "Fallback to general information about Argos due to an error in tool selection"
                    }]
                    logger.warning("Using fallback tool call due to API error")
                    break

            # # Display tool selection decisions
            # formatted_tool_decision = Text()
            # formatted_tool_decision.append("Tool Decision Summary\n", style="bold underline")

            # # Add the overall reasoning from the model if available
            # overall_reasoning = ""
            # try:
            #     # Check if completion exists and has the necessary structure
            #     if 'completion' in locals() and completion and completion.choices and completion.choices[0].message:
            #        overall_reasoning = completion.choices[0].message.reasoning
            #     else:
            #         # Handle cases where completion object doesn't exist or is incomplete
            #         overall_reasoning = "Overall reasoning not available (completion object missing or incomplete)."
            #         logger.debug("Completion object missing or incomplete for overall reasoning extraction.")
            # except AttributeError:
            #      # Handle cases where the structure might be different or reasoning attribute is missing
            #      overall_reasoning = "Overall reasoning not available (AttributeError)."
            #      logger.debug("AttributeError while extracting overall reasoning from completion object.")

            # if overall_reasoning:
            #     formatted_tool_decision.append("\nOverall Reasoning:\n", style="bold magenta")
            #     # Append the reasoning string directly
            #     formatted_tool_decision.append(overall_reasoning, style="magenta")
            #     formatted_tool_decision.append("\n" + "-"*20 + "\n", style="dim") # Separator

            # formatted_tool_decision.append(f"Tool Calls: {len(tool_calls)}\n", style="bold")
            
            # for i, tool_call in enumerate(tool_calls, 1):
            #     formatted_tool_decision.append(f"\nTool Call {i}:\n", style="bold")
            #     formatted_tool_decision.append(f"Name: {tool_call['name']}\n")
            #     formatted_tool_decision.append("Arguments:\n")
            #     for key, value in tool_call['args'].items():
            #         formatted_tool_decision.append(f"  {key}: {value}\n")
            #     formatted_tool_decision.append(f"Reasoning: {tool_call['reasoning']}\n")
                
            # panel = Panel(
            #     formatted_tool_decision,
            #     style="white on black",
            #     border_style="yellow",
            #     title="[TOOL DECISIONS]",
            #     title_align="left",
            #     expand=True,
            # )
            # console.print(panel)

            # Emit tool-specific status update *after* invocation completes
            await self.emit_event(
                        {
                            "type": "status",
                            "data": {
                                "description": f"{len(tool_calls)} research tool{'s' if len(tool_calls) != 1 else ''} selected",
                                "done": False,
                            },
                        }
            )

            # Only print if logging level is INFO or below
            if logger.isEnabledFor(logging.INFO):
                console.print("\n[bold yellow]" + "="*50 + "\n" +
                                "START OF TOOL CALLS\n" + 
                                "="*50 + "[/bold yellow]\n")

            # Execute all tools in parallel using asyncio.gather
            async def process_tool_call(tool_call):
                
                # Debug logging level right before the conditional check
                # print(f"DEBUG - Logger level before tool call: {logger.level} (ERROR={logging.ERROR}, INFO={logging.INFO}, DEBUG={logging.DEBUG})")
                # print(f"DEBUG - Is INFO enabled? {logger.isEnabledFor(logging.INFO)}")
                
                if logger.isEnabledFor(logging.INFO):
                    # Display tool call details for debugging
                    formatted_tool_call = Text()
                    formatted_tool_call.append(f"Processing Tool Call: {tool_call['name']}\n", style="bold underline")
                    formatted_tool_call.append("Arguments:\n")
                    for key, value in tool_call['args'].items():
                        formatted_tool_call.append(f"  {key}: {value}\n")
                    formatted_tool_call.append(f"Reasoning: {tool_call['reasoning']}\n")
                    panel = Panel(
                        formatted_tool_call,
                        style="white on black",
                        border_style="blue",
                        title="[PROCESSING TOOL]",
                        title_align="left",
                        expand=True,
                    )
                    console.print(panel)
                
                # Select the appropriate tool function based on name
                tool_functions = {
                    "get_armed_conflict_data_by_country": get_armed_conflict_data_by_country,
                    "get_armed_conflict_data_by_non_state_actor": get_armed_conflict_data_by_non_state_actor,
                    "get_armed_conflict_data_by_organization": get_armed_conflict_data_by_organization,
                    "get_armed_conflict_data_by_region": get_armed_conflict_data_by_region,
                    "get_information_about_RULAC": get_information_about_RULAC,
                    "get_RULAC_conflict_classification_methodology": get_RULAC_conflict_classification_methodology,
                    "get_international_law_framework": get_international_law_framework,
                    "get_information_about_Argos": get_information_about_Argos,
                    "brave_search": brave_search,
                    "get_human_rights_research_by_country": get_human_rights_research_by_country,
                    "get_combined_news": get_combined_news
                }
                
                if tool_call["name"] not in tool_functions:
                    logger.warning(f"Unknown tool: {tool_call['name']}")
                    return None
                
                selected_tool = tool_functions[tool_call["name"]]
                
                # Fix missing parameters based on known tool requirements
                fixed_args = tool_call["args"].copy()
                
                # Special handling for specific tools with known required parameters
                if tool_call["name"] == "get_armed_conflict_data_by_country":
                    # Ensure countries parameter exists as a list
                    if "countries" not in fixed_args or not isinstance(fixed_args["countries"], list):
                        if "countries" in fixed_args and isinstance(fixed_args["countries"], str):
                            # Convert string to list with one element
                            fixed_args["countries"] = [fixed_args["countries"]]
                        else:
                            # Default empty list
                            fixed_args["countries"] = []
                    
                    # Ensure conflict_types parameter exists as a list
                    if "conflict_types" not in fixed_args:
                        fixed_args["conflict_types"] = []
                        logger.warning(f"Added missing required parameter 'conflict_types' with default value []")
                
                # Similar fixes for other tools
                if tool_call["name"] == "get_armed_conflict_data_by_non_state_actor":
                    if "non_state_actors" not in fixed_args or not isinstance(fixed_args["non_state_actors"], list):
                        if "non_state_actors" in fixed_args and isinstance(fixed_args["non_state_actors"], str):
                            fixed_args["non_state_actors"] = [fixed_args["non_state_actors"]]
                        else:
                            fixed_args["non_state_actors"] = []
                
                if tool_call["name"] == "get_armed_conflict_data_by_organization":
                    if "organizations" not in fixed_args or not isinstance(fixed_args["organizations"], list):
                        if "organizations" in fixed_args and isinstance(fixed_args["organizations"], str):
                            fixed_args["organizations"] = [fixed_args["organizations"]]
                        else:
                            fixed_args["organizations"] = []
                    if "conflict_types" not in fixed_args:
                        fixed_args["conflict_types"] = []
                
                if tool_call["name"] == "get_armed_conflict_data_by_region":
                    if "regions" not in fixed_args or not isinstance(fixed_args["regions"], list):
                        if "regions" in fixed_args and isinstance(fixed_args["regions"], str):
                            fixed_args["regions"] = [fixed_args["regions"]]
                        else:
                            fixed_args["regions"] = []
                    if "conflict_types" not in fixed_args:
                        fixed_args["conflict_types"] = []
                
                if tool_call["name"] == "get_international_law_framework" and "law_focus" not in fixed_args:
                    fixed_args["law_focus"] = "International Humanitarian Law (IHL)"
                
                if tool_call["name"] == "get_human_rights_research_by_country" and "country" not in fixed_args:
                    fixed_args["country"] = "Unknown"
                
                if tool_call["name"] == "brave_search" and "query" not in fixed_args:
                    fixed_args["query"] = "Missing query"
                
                if tool_call["name"] == "get_combined_news" and "search_query" not in fixed_args:
                    fixed_args["search_query"] = "Current news"
                
                # Log if any parameters were fixed
                if fixed_args != tool_call["args"]:
                    logger.warning(f"Fixed tool arguments for {tool_call['name']}: {tool_call['args']} -> {fixed_args}")
                    # Update the tool_call with fixed arguments for logging/display
                    tool_call["args"] = fixed_args

                # Get tool-specific friendly name for UI status
                tool_name = tool_call["name"]
                friendly_description = self.tool_friendly_names.get(
                    tool_name, 
                    f"🔍 Researching with {tool_name}..."
                )

                # Add detailed tool params to status (optional)
                if tool_name == "get_armed_conflict_data_by_country" and "countries" in tool_call["args"]:
                    countries = tool_call["args"]["countries"]
                    if isinstance(countries, list) and countries:
                        country_names = " and ".join(countries)
                        friendly_description = f"Analyzing RULAC conflict profiles on '{country_names}'"
                elif tool_name == "get_human_rights_research_by_country" and "country" in tool_call["args"]:
                    country = tool_call["args"]["country"]
                    friendly_description = f"Analyzing HRW human rights research on '{country}'"
                elif tool_name == "brave_search" and "query" in tool_call["args"]:
                    query = tool_call["args"]["query"]
                    friendly_description = f"Searching web for '{query}'"
                elif tool_name == "get_international_law_framework" and "law_focus" in tool_call["args"]:
                    law_focus = tool_call["args"]["law_focus"]
                    friendly_description = f"Analyzing framework on '{law_focus}'"
                elif tool_name == "get_RULAC_conflict_classification_methodology":
                    friendly_description = f"Analyzing RULAC conflict classification methodology"
                elif tool_name == "get_combined_news" and "search_query" in tool_call["args"]:
                    query = tool_call["args"]["search_query"]
                    friendly_description = f"Checking developments on '{query}'"

                # Execute the tool and return results
                try:
                    tool_output = await selected_tool.ainvoke(fixed_args)
                    
                    # Emit tool-specific status update *after* invocation completes
                    # --- Add Lock and Delay Logic ---
                    async with self.tool_status_lock:
                        if self.is_first_tool_status_update:
                            # First tool update, emit immediately and set flag
                            self.is_first_tool_status_update = False
                        else:
                            # Subsequent tool updates, wait 2 seconds
                            await asyncio.sleep(2)
                        
                        # Now emit the event
                        await self.emit_event(
                            {
                                "type": "status",
                                "data": {
                                    "description": friendly_description,
                                    "done": False,
                                },
                            }
                        )
                    # --- End Lock and Delay Logic ---

                    # Process the output
                    if isinstance(tool_output, dict) and "content" in tool_output and "citations" in tool_output:
                        content = tool_output["content"]
                        citations = tool_output["citations"]
                        
                        # Process citations
                        if citations and isinstance(citations, list):
                            for citation in citations:
                                if isinstance(citation, dict) and "url" in citation:
                                    citation_url = citation.get("url", "")
                                    citation_title = citation.get("title", "Source")
                                    formatted_content = citation.get("formatted_content", "")
                                    
                                    # Only emit new citations to avoid duplicates, unless it's a Brave search result
                                    should_emit_citation = citation_url and (
                                        citation_url == "https://search.brave.com" or 
                                        citation_url not in self.global_unique_citations_retreived
                                    )
                                    
                                    if should_emit_citation:
                                        # Create citation event for UI
                                        citation_event = {
                                            "type": "citation",
                                            "data": {
                                                "document": [formatted_content],
                                                "metadata": [
                                                    {
                                                        "date_accessed": datetime.now().isoformat(),
                                                        "source": citation_title,
                                                    }
                                                ],
                                                "source": {
                                                    "name": citation_url.replace('http://www.', '').replace('https://www.', '').replace('http://', '').replace('https://', ''), 
                                                    "url": citation_url
                                                },
                                            }
                                        }

                                        # Emit citation event to UI
                                        await self.emit_event(citation_event)
                                        # logger.info(f"Emitted citation event: {citation_event}")
                                        # Track citation count
                                        self.global_citation_count += 1
                                        # Track unique URLs, making Brave URLs unique for the set
                                        if should_emit_citation:
                                            if citation_url == "https://search.brave.com":
                                                # Append count to make Brave URL unique in the set
                                                unique_brave_url = f"{citation_url}#{self.global_citation_count}" 
                                                self.global_unique_citations_retreived.add(unique_brave_url)
                                            elif citation_url not in self.global_unique_citations_retreived:
                                                # Add other URLs only if they are new
                                                self.global_unique_citations_retreived.add(citation_url)
                        
                        # Return formatted output
                        return {
                            "tool_name": tool_call["name"],
                            "tool_call_id": tool_call["id"],
                            "content": content,
                            "args": tool_call["args"],
                            "reasoning": tool_call["reasoning"]
                        }
                    else:
                        # Handle non-standard tool outputs
                        return {
                            "tool_name": tool_call["name"],
                            "tool_call_id": tool_call["id"],
                            "content": tool_output,
                            "args": tool_call["args"],
                            "reasoning": tool_call["reasoning"]
                        }
                except Exception as e:
                    # Handle tool execution errors
                    panel = Panel.fit(
                        f"❌ Error invoking tool {tool_call['name']}:\n{e}",
                        style="white on red",
                        border_style="red",
                    )
                    console.print(panel)
                    logger.error(f"Tool execution error: {e}")
                    
                    # Return error information
                    return {
                        "tool_name": tool_call["name"],
                        "tool_call_id": tool_call["id"],
                        "content": f"Error executing tool: {str(e)}",
                        "error": True,
                        "args": tool_call["args"],
                        "reasoning": tool_call["reasoning"]
                    }

            # Create tasks to run in parallel
            tool_tasks = [process_tool_call(tool_call) for tool_call in tool_calls]
            
            # Execute all tools in parallel
            logger.info(f"Running {len(tool_tasks)} tool tasks in parallel")
            # Reset the flag before starting parallel tasks
            self.is_first_tool_status_update = True
            tool_results = await asyncio.gather(*tool_tasks)
            
            # Filter out None results and add to tool_outputs
            for result in tool_results:
                if result is not None:
                    tool_outputs.append(result)

            # Only print if logging level is INFO or below
            if logger.isEnabledFor(logging.INFO):
                console.print("\n[bold yellow]" + "="*50 + "\n" +
                                "END OF TOOL CALLS\n" + 
                                "="*50 + "[/bold yellow]\n")

            # Log summary of tool execution
            logger.debug(f"Collected {len(tool_outputs)} tool outputs")
            logger.info(f"Successfully emitted all collected citations: {self.global_citation_count}")

            # Only print if logging level is INFO or below
            if logger.isEnabledFor(logging.INFO):
                console.print("\n[bold yellow]" + "="*50 + "\n" +
                                "END OF TOOL USE AGENT\n" + 
                                "="*50 + "[/bold yellow]\n")

            # Return collected tool outputs for final response generation
            return tool_outputs

        except Exception as e:
            # Handle overall process errors
            logger.error(f"Error during tool model execution: {e}")
            return [{
                "tool_name": "get_information_about_Argos",
                "tool_call_id": "error_recovery",
                "content": "I encountered an error while trying to process your request. I'll provide general information about my capabilities instead.",
                "args": {},
                "reasoning": "Error during tool model execution"
            }]

    def handle_tool_query_final_response(self, tool_outputs: list[dict], original_messages: list[dict]) -> Generator[str, None, None]:
        """
        Generates the final response after all research tools have been executed.
        
        This function:
        1. Processes and organizes research outputs by category (RULAC, HRW, News, etc.)
        2. Combines all research into a structured format
        3. Creates a comprehensive system prompt with the research results
        4. Sends the prompt and original conversation to the final LLM
        5. Streams the generated response back to the user
        
        Args:
            tool_outputs: List of dictionaries containing tool outputs and metadata
            original_messages: Original conversation messages from the user
            
        Returns:
            Generator that streams the final response tokens
        """
        logger.debug("Inside final tool query response function...")
        logger.debug(f"Processing {len(tool_outputs)} tool outputs with {len(original_messages)} original messages")

        # Debug log the structure of an example tool output
        if tool_outputs:
            example_output = tool_outputs[0]
            logger.debug(f"Example tool output structure: {list(example_output.keys())}")
            logger.debug(f"Example tool name: {example_output.get('tool_name', 'N/A')}")
            content_preview = example_output.get('content', '')[:100] + '...' if len(example_output.get('content', '')) > 100 else example_output.get('content', '')
            logger.debug(f"Example content preview: {content_preview}")

        # STEP 1: Categorize research outputs by source/type
        rulac_outputs = []      # RULAC research data
        hrw_outputs = []        # Human Rights Watch reports
        argos_outputs = []     # Information about Argos itself
        web_outputs = []        # General web content
        news_outputs = []       # News content

        # Process each tool output
        for output in tool_outputs:
            # Skip empty outputs
            if not output or not output.get("content"):
                continue
                
            # Get the tool name and content
            tool_name = output.get("tool_name", "unknown")
            content = output.get("content", "")
            
            # Log which tool is being processed
            logger.debug(f"Processing output from tool: {tool_name}")
            
            # Categorize by tool source/type
            tool_source = output.get("tool_source", "unknown").upper()
            
            if any(rulac_tool in tool_name for rulac_tool in ["get_information_about_RULAC", "get_international_law_framework", "get_RULAC_conflict_classification_methodology", "get_armed_conflict_data"]):
                rulac_outputs.append(output)
                logger.debug(f"Added RULAC output: {tool_name}")
            elif tool_name == "get_human_rights_research_by_country":
                hrw_outputs.append(content)
                logger.debug(f"Added HRW output: {tool_name}")
            elif "get_information_about_Argos" in tool_name:
                argos_outputs.append(content)
                logger.debug(f"Added Argos info: {tool_name}")
            elif "get_combined_news" in tool_name:
                news_outputs.append(content)
                logger.debug(f"Added News output: {tool_name}")
            elif "brave_search" in tool_name:
                web_outputs.append(content)
                logger.debug(f"Added Web output: {tool_name}")
            else:
                # Default category for unknown sources
                web_outputs.append(content)
                logger.debug(f"Added to Web (default) category: {tool_name}")
        
        # STEP 2: Combine research outputs with appropriate headers and organization
        combined_research = ""
        
        # Add RULAC outputs in a specific, logical order
        if rulac_outputs:
            # Define preferred order of RULAC tools
            rulac_order = [
                "get_information_about_RULAC",
                "get_international_law_framework",
                "get_RULAC_conflict_classification_methodology",
                "get_armed_conflict_data_by_region",
                "get_armed_conflict_data_by_organization",
                "get_armed_conflict_data_by_non_state_actor",
                "get_armed_conflict_data_by_country"
            ]
            
            # Sort RULAC outputs according to defined order
            ordered_rulac_outputs = []
            for tool_name in rulac_order:
                for output in rulac_outputs:
                    if output["tool_name"] == tool_name:
                        ordered_rulac_outputs.append(output["content"])
            
            # Add any remaining outputs not in the predefined order
            for output in rulac_outputs:
                if output["tool_name"] not in rulac_order:
                    ordered_rulac_outputs.append(output["content"])
            
            # Add RULAC section with header
            combined_research += "<RULAC_research>\n## Rule of Law in Armed Conflict (RULAC) research\n\n" 
            combined_research += "The Rule of Law in Armed Conflict (RULAC) portal provides the the most authoritative classifications of armed conflicts based on the parties involved and the nature of the hostilities."
            combined_research += "\n\n" + "\n\n- - -\n\n".join(ordered_rulac_outputs) 
            combined_research += "\n\n</RULAC_research>"
        
        # Add Human Rights Watch outputs
        if hrw_outputs:
            combined_research += "\n\n<HRW_research>\n## Human Rights Watch (HRW) research\n\n"
            combined_research += "Human Rights Watch (HRW) is a non-governmental organization that monitors human rights violations and abuses around the world."
            combined_research += "\n\n" + "\n\n".join(hrw_outputs)
            combined_research += "\n\n</HRW_research>"

        # Add Web Research outputs
        if web_outputs:
            combined_research += "\n\n<web_research>\n## web research\n\n"
            combined_research += "\n\n".join(web_outputs) 
            combined_research += "\n\n</web_research>"

        # Add Argos information
        if argos_outputs:
            combined_research += "\n\n<Argos_information>\n## argos information\n\n"
            combined_research += "\n\n".join(argos_outputs)
            combined_research += "\n\n</Argos_information>"

        # Add latest news
        if news_outputs:
            combined_research += "\n\n<latest_news_and_developments>\n## latest news and developments\n\n"
            combined_research += "".join(news_outputs)
            combined_research += "\n\n</latest_news_and_developments>"

        # Log summary of combined research
        logger.debug(f"Combined research length: {len(combined_research)} characters")
        logger.info(f"RULAC outputs: {len(rulac_outputs)}, HRW outputs: {len(hrw_outputs)}, News outputs: {len(news_outputs)}, Web outputs: {len(web_outputs)}, Argos outputs: {len(argos_outputs)}")

        # # I want to log out a sample of each of the outputs
        # if rulac_outputs:
        #     logger.info(f"Sample of RULAC outputs: {rulac_outputs[0]['content'][:500]}\n\n")
        # if hrw_outputs:
        #     logger.info(f"Sample of HRW outputs: {hrw_outputs[0][:500]}\n\n")
        if news_outputs:
            for output in news_outputs:
                logger.info(f"Sample of News outputs: {output}\n\n")
        if web_outputs:
            for output in web_outputs:
                logger.info(f"Sample of Web outputs: {output}\n\n")
        # if argos_outputs:
        #     logger.info(f"Sample of Argos outputs: {argos_outputs[0][:500]}\n\n")

        # STEP 3: Prepare the final system prompt with the research
        currentDateTime = datetime.now(ZoneInfo("Europe/Paris")).strftime("%B %d, %Y %I:%M %p")
        
        # Separate the conversation into two parts: without the last user message and the last user message itself
        conversation_without_last_user_message = ""
        last_user_message = ""
        
        # Extract the last user message and build conversation history
        filtered_messages = []
        for msg in original_messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            # Only include user and assistant messages
            if role in ["user", "assistant"] and content:
                filtered_messages.append({"role": role, "content": content})
        
        # Find the last user message
        for i in range(len(filtered_messages) - 1, -1, -1):
            if filtered_messages[i]["role"] == "user":
                last_user_message = filtered_messages[i]["content"]
                # Remove the last user message from the conversation history
                filtered_messages.pop(i)
                break
        
        # Format the conversation history
        for msg in filtered_messages:
            role_display = "User" if msg["role"] == "user" else "Assistant"
            conversation_without_last_user_message += f"\n\n**{role_display}**: {msg['content']}"
        
        # Check if we have a conversation history and format it properly
        if conversation_without_last_user_message:
            conversation_without_last_user_message = conversation_without_last_user_message.strip()
            # Also adding "Conversation History" header information for prompt
            conversation_without_last_user_message = f"--- \n\n# Our current conversation\n\nWe are currently having the following conversation:\n\n{conversation_without_last_user_message}"
       
        # Check if we have a last user message
        if not last_user_message:
            last_user_message = "Please provide information about the current international conflicts."
        
        # STEP 3: Choose the correct prompt template based on the model
        # model_name = "deepseek-r1-distill-qwen-32b" #has now been deprecated and replaced with qwen/qwen3-32b
        model_name = "qwen/qwen3-32b"


        
        # Import the new Deepseek-specific prompt template
        import prompts.final_prompts.final_tool_prompt_for_Deepseek as final_tool_prompt_deepseek
        DEEPSEEK_PROMPT_TEMPLATE = final_tool_prompt_deepseek.PROMPT
        
        # Render the Deepseek-specific prompt with the required variables
        rendered_system_prompt = DEEPSEEK_PROMPT_TEMPLATE.replace(
            "{currentDateTime}", currentDateTime
        ).replace(
            "{combined_tool_research}", combined_research
        ).replace(
            "{conversation_without_last_user_message}", conversation_without_last_user_message
        ).replace(
            "{last_user_message}", last_user_message
        )
        
        # Display debug information about prompt
        # logger.info(f"System prompt template length: {len(DEEPSEEK_PROMPT_TEMPLATE)}")
        logger.info(f"Final system prompt length: {len(rendered_system_prompt)} characters")
        
        # if logger.isEnabledFor(logging.INFO):
        #     # Truncate the system prompt for debug display, only show last 1000 characters
        #     debuggingSystemPrompt = rendered_system_prompt[-1000:]
        #     # Display the system prompt in a rich panel
        #     panel = Panel(
        #         Markdown(debuggingSystemPrompt),
        #         style="white on black",
        #         border_style="cyan",
        #         title="[bold]System Prompt Preview[/bold]",
        #         title_align="left",
        #         width=120
        #     )
        #     console.print(panel)
      
        # STEP 4: Create the final messages for the LLM
        # For Deepseek, we need to package everything into a single user message
        final_messages = [
            {"role": "user", "content": rendered_system_prompt}
        ]
        
        # Log final prompt with all messages
        # log_final_messages(final_messages, "Research Agent Complete Messages")
        
        # STEP 5: Set up the LLM client for generating the final response
        chat_client = Groq(api_key=self.valves.groq_api_key)
        logger.debug("Starting final tool use LLM response synchronous streaming...")

        # STEP 6: Set up the LLM client for generating and streaming the final response
        # Add detailed tracking of API call
        api_params = {
            "model": model_name,
            "temperature": 0.6,
            "max_completion_tokens": 4096,
            "top_p": 0.95,
            "stream": True,
            # "reasoning_format": "raw", #this is the default for deepseek
            "reasoning_format": "parsed", #this is the default for qwen/qwen3-32b
            "message_count": len(final_messages),
            "prompt_tokens_estimate": sum(len(m.get("content", "")) for m in final_messages) // 4
        }
        
        log_api_request("Groq", model_name, api_params)

        # STEP 6: Stream the final response from the LLM with improved error handling and retries
        max_retries = 3
        retry_count = 0
        backoff_time = 1  # Initial backoff in seconds
        
        while retry_count <= max_retries:
            try:
                start_time = time.time()
                logger.info(f"Invoking Groq LLM ({model_name}) - Attempt {retry_count + 1}/{max_retries + 1}")
                
                completion = chat_client.chat.completions.create(
                    model=model_name,
                    messages=final_messages,
                    temperature=0.6,
                    max_completion_tokens=4096,
                    top_p=0.95,
                    stream=True,
                    reasoning_format="raw"
                )
                
                # Process streaming chunks and yield to caller
                chunk_count = 0
                first_token_time = None
                
                for chunk in completion:
                    chunk_count += 1
                    
                    # Record time to first token
                    if chunk_count == 1:
                        first_token_time = time.time()
                        time_to_first_token = first_token_time - start_time
                        logger.info(f"Time to first token: {time_to_first_token:.2f}s")
                    
                    # Log chunk progress periodically
                    if chunk_count % 10 == 0:
                        # logger.debug(f"Processing chunk {chunk_count}...")
                        pass
                    
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        pass
                    else:
                        logger.debug(f"Chunk {chunk_count} has no content.")
                
                # Log successful completion metrics
                completion_time = time.time() - start_time
                log_api_response_time("Groq", model_name, start_time)
                logger.info(f"Finished streaming: processed {chunk_count} chunks in {completion_time:.2f}s")
                
                # Successful completion, break out of retry loop
                break
                
            except Exception as e:
                retry_count += 1
                log_api_response_time("Groq", model_name, start_time, status="error")
                
                # Enhanced error reporting
                error_type = type(e).__name__
                error_details = str(e)
                
                # Log detailed error information
                logger.error(f"API Error ({error_type}): {error_details}")
                
                # Create a detailed error panel for inspection
                error_panel = Panel(
                    f"Error Type: {error_type}\nDetails: {error_details}",
                    title="LLM API Error",
                    border_style="red",
                    expand=False
                )
                console.print(error_panel)
                
                # Check if we should retry
                if retry_count <= max_retries:
                    # Calculate backoff with exponential increase
                    wait_time = backoff_time * (2 ** (retry_count - 1))
                    logger.warning(f"Retrying in {wait_time:.1f}s (attempt {retry_count}/{max_retries})")
                    
                    # Yield a message to the user about the retry
                    yield f"\n[Experiencing a temporary issue. Retrying... ({retry_count}/{max_retries})]\n"
                    
                    # Wait before retry
                    time.sleep(wait_time)
                    
                    # Try alternative model if available and we're on the last retry
                    if retry_count == max_retries:
                        alt_model = "llama-3.1-8b-instant"
                        logger.info(f"Trying alternative model: {alt_model}")
                        yield f"\n[Switching to alternative model due to service issues...]\n"
                        
                        try:
                            log_api_request("Groq", alt_model)
                            alt_start_time = time.time()
                            
                            alt_completion = chat_client.chat.completions.create(
                                model=alt_model,
                                messages=final_messages,
                                temperature=0.2,
                                stream=True
                            )
                            
                            for chunk in alt_completion:
                                if chunk.choices[0].delta.content:
                                    yield chunk.choices[0].delta.content
                            
                            log_api_response_time("Groq", alt_model, alt_start_time)
                            break
                            
                        except Exception as alt_e:
                            log_api_response_time("Groq", alt_model, alt_start_time, "error")
                            logger.error(f"Alternative model also failed: {alt_e}")
                else:
                    # If all retries failed, yield a helpful error message
                    error_message = (
                        f"\n\nI apologize, but I'm experiencing technical difficulties connecting to my knowledge services. "
                        f"Error details: {error_type} - {error_details}\n\n"
                        f"Please try again in a few moments. If the problem persists, it may indicate an issue with the external API service."
                    )
                    yield error_message




            # trying with deepseek
            # Convert to OpenAI message format
            # openai_messages = convert_to_openai_messages(messages)
            # console.print(f"OpenAI converted messages w roles: {openai_messages}")
            # client = OpenAI(api_key=self.valves.deepseek_api_key, base_url="https://api.deepseek.com")
            # response = client.chat.completions.create(
            #     messages=openai_messages,
            #     stream=True
            # )
            # return response.choices[0].message.content

            # trying with mistral
            # Convert to OpenAI message format
            # openai_messages = convert_to_openai_messages(messages)
            # console.print(f"OpenAI converted messages w roles: {openai_messages}")
            # client = Mistral(api_key=self.valves.mistral_api_key)
            # chat_response = client.chat.complete(
            #     model="mistral-large-latest", temperature=0,
            #     messages = openai_messages
            # )
            # print(chat_response.choices[0].message.content)
            # return chat_response.choices[0].message.content





# TESTING PIPE
# Note: there are other test functions in the tests/test_router.py file
# This is a simple test function to test the pipe with a single user message

def test_pipe():
    """
    Basic test function for the Argos pipeline.
    """
    # Initialize the Pipe with local testing enabled
    pipe = Pipe(local_testing=True)

    # Mock user data
    __user__ = {
        "id": "test123",
        "email": "test@example.com", 
        "name": "Test User",
        "role": "tester"
    }
    
    # Mock request (not used in local testing)
    __request__ = None

    async def run_test():
        # Test conversation
        test_messages = {
            # Full conversation history with shared context about human rights in Russia
            # "messages": [
            #     {"role": "user", "content": "I'm researching human rights situations in different countries. Can you tell me about Russia?"},
            #     {"role": "assistant", "content": "I'd be happy to help with your research on human rights in Russia. Russia has a complex human rights record with various concerns raised by international organizations. Would you like me to focus on any specific aspects of human rights in Russia, such as freedom of expression, political rights, or treatment of minorities?"},
            #     {"role": "user", "content": "Yes, please tell me about freedom of expression and political rights in Russia."},
            #     {"role": "assistant", "content": "Regarding freedom of expression and political rights in Russia:\n\n**Freedom of Expression:**\n- Media outlets face significant restrictions, with many independent media organizations labeled as \"foreign agents\"\n- Internet censorship has increased, with authorities blocking websites and platforms\n- Journalists reporting on sensitive topics have faced harassment, prosecution, and in some cases violence\n\n**Political Rights:**\n- Opposition figures have reported obstacles to participating in elections\n- Public demonstrations require advance approval, and unauthorized protests often result in detentions\n- Several opposition leaders and activists have faced legal challenges, including imprisonment\n\nWould you like more specific information about any of these points or information about other human rights aspects in Russia?"},
            #     {"role": "user", "content": "How does this compare to the human rights situation in the USA?"}
            # ]
            "messages": [
                # {"role": "user", "content": "What is the latest news on the situation in Ukraine? How is the conflict classified in Ukraine?"}
                # {"role": "user", "content": "Who is the current prime minister of France? Is there a conflict in Ukraine according to RULAC?"}
            #     #  {"role": "user", "content": "I'm curious about Ukraine. How is the conflict classified in Ukraine? What has Ukraine done to protect human rights in terms of the Rome Statute?"}
                # {"role": "user", "content": "Has Ukraine signed the Rome Statute according to HRW?"}
                # {"role": "user", "content": "is russia or usa more dangerous for human rights? why?"}
                # {"role": "user", "content": "what conflicts are taking place in USA and Russia?"}
            #     # {"role": "user", "content": "what is the diff between france and russia's human rights records in LGBT rights?  what are the similiarities?"}
                # {"role": "user", "content": "what is international human rights law?"}
                # {"role": "user", "content": "what is RULAC and who made it? How do they classify the conflict in Ukraine? What about the conflict in Syria?"}
                # {"role": "user", "content": "what is the difference between international humanitarian law and international human rights law? What role does the UN and ECJ play in this? How are war crimes prosecuted? Does the ICC essentially prosecute IHL violations?"},
            #     # {"role": "user", "content": "how does RULAC classify the conflict in france?"},
                # {"role": "user", "content": "what are your capabilities? Is there a conflict in Ukraine according to RULAC?"},
                # {"role": "user", "content": "who is the voguer vinii revlon? what is the house of revlon?"},
                # {"role": "user", "content": "who is the creator of Argos? "},
                # {"role": "user", "content": "who is president of somalia and sudan?"},

                # {"role": "user", "content": "what is your name? What tasks can you perform? "},
                {"role": "user", "content": "How is the Ukraine conflict classified? and who is the current prime minister of France?"},
                # {"role": "user", "content": "what is the latest news on the situation in Ukraine? Is there a ceasefire?"}
            #     # {"role": "user", "content": "how is the conflict in ukraine classified? what is the applicable IHL law? and can you give me a timeline of the conflict's key events?"}
                 
            ]
        }

        # Track execution time
        start_time = time.time()
        
        # Run the pipeline
        response = await pipe.pipe(
            test_messages,
            __user__,
            __request__,
            local_testing=True
        )

        # Calculate execution time
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Display execution time
        console.print(f"\n[green]✓ Test completed in {execution_time:.2f} seconds[/]")

        # Collect and display response
        final_answer = ""
        print("\nStreaming response:")
        for token in response:
            # print(token, end="")
            final_answer += token

        # Display final answer in formatted panel
        panel = Panel(
            Markdown(final_answer),
            style="white on black",
            border_style="purple3",
            title="Test Response",
            title_align="left"
        )
        console.print("\n")
        console.print(panel)

    # Run the test
    asyncio.run(run_test())



def test_title_generation():
    """Test the title generation functionality of the pipeline"""
    # Initialize the Pipe with local testing enabled
    pipe = Pipe(local_testing=True)

    # Mock user data
    __user__ = {
        "id": "test123",
        "email": "test@example.com", 
        "name": "Test User",
        "role": "tester"
    }

    # Sample body with query for title generation
    test_body = {
        "model": "argos_agent_v1_mar_2025",
        "messages": [{
            "role": "user",
            "content": """Here is the query:
What is the human rights situation in Somalia?

Create a concise, 3-5 word phrase as a title for the previous query. Avoid quotation marks or special formatting. RESPOND ONLY WITH THE TITLE TEXT.

Examples of titles:
Ukraine Conflict Classification
Uganda Press Freedom
Racial Justice in USA
EU Judicial Reform
LGBTQ+ Rights in China"""
        }],
        "stream": False,
        "max_completion_tokens": 1000
    }

    async def run_test():
        print("\n[bold yellow]Testing Title Generation[/]")
        result = await pipe.pipe(
            test_body, 
            __user__, 
            None, 
            local_testing=True,
            __task__="title_generation"
        )
        print(f"\nGenerated Title: {result}")

    # Run the test
    asyncio.run(run_test())

if __name__ == "__main__":
    test_pipe()
    print("\n" + "="*50 + "\n")
    # test_title_generation()

