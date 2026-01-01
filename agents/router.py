"""
Router module for Beacon

This module provides routing functionality to determine whether a user query
should be handled by the general LLM or the research tool LLM. It also provides a rewritten user task based on the full conversation history, which is
useful for the tool-use LLM to use as more streamlined context.
"""
from typing import Any
import json
import logging
import asyncio
import groq
import instructor
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text
from rich.style import Style
from rich.theme import Theme
from rich.box import ROUNDED
import coloredlogs

# Define custom theme for rich console output
custom_theme = Theme({
    # Base logging colors - modern palette
    "debug": "dim #94e2d5",        # Teal - subtle but readable
    "info": "#89b4fa",             # Bright blue - clear and modern
    "warning": "#f9e2af",          # Soft yellow - attention but not harsh
    "error": "bold #f38ba8",       # Soft red - stands out without being too aggressive
    
    # Router theme - using modern color combinations
    "router.debug": "white on #1e1e2e",      # Dark background with white text
    "router.debug.border": "#cba6f7",        # Purple border - distinctive
    "router.info": "white on #313244",       # Darker background for info panels
    "router.info.border": "#89b4fa",         # Blue border to match info color
    
    # Additional distinctive colors for different message types
    "router.success": "#a6e3a1",             # Green for success messages
    "router.process": "#f5c2e7",             # Pink for processing status
    "router.highlight": "bold #fab387"       # Orange for highlights
})

# Configure logging for debug
logger = logging.getLogger("Beacon.Router")

coloredlogs.install(
    logger=logger,
    level="INFO",
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    )

# Initialize Rich Console with theme
console = Console(theme=custom_theme)


# Type definitions
class RouterResponse(BaseModel):
    """Router Response from a User New Message"""
    conversational_context: str = Field(..., description="A summary of the conversation context synthesized")
    reasoning: str = Field(..., description="Explanation of the decisions made when synthesizing the user task")
    router_decision: str = Field(..., description="A routing decision either BEACON_BASE_AGENT or RESEARCH_AGENT")
    task: str = Field(..., description="A rewritten user task based on full conversation context and including all entities for which the user is seeking information.")
    news_search_by_topic: str = Field(..., description="A news search query optimized for finding relevant news articles about the user's topic")


# Helper function to compile conversation
def compile_conversation(conversation_messages: list[dict]) -> str:
    """
    Turns a list of messages into a single text block for the prompt.
    Each message is labeled by role, then the content.
    """
    text_blocks = []
    for msg in conversation_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        text_blocks.append(f"{role.upper()}: {content}")
    return "\n".join(text_blocks)


class Router:
    """Router class that analyzes user intent and determines which LLM to use"""
    # When used within the Beacon pipeline, the router model is passed in as a parameter
    # When used standalone, the router model is initialized here
    def __init__(self, router_model=None, groq_api_key: str = None):
        """
        Initialize router with a language model.
        
        Args:
            router_model: Optional router model (legacy support)
            groq_api_key: Optional Groq API key. If not provided, uses environment variable.
        """
        # Router LLM setup
        import os
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.model_name = "gemma2-9b-it" # or llama-3.1-8b-instant
        self.temperature = 0
        
        # Store router_model if provided (legacy support)
        self.router_model = router_model
        
        # client will be initialized when needed
        self.client = None
        
    async def route(self, conversation_messages: list[dict]) -> RouterResponse:
        """
        Router analyzes the user's intent (by taking into account the full conversation history) 
        to identify the user task. It also determines if the user's task would benefit from 
        any available research tools (in which case it is routed to the tool-use LLM), 
        otherwise it is routed to the generalist LLM.
        
        Args:
            conversation_messages: The entire messages conversation (not just last user message)
            
        Returns:
            A RouterResponse object indicating the user task and routing decision
        """
        # Initialize Groq client if not already done
        if self.client is None:
            # Initialize Groq client and patch with instructor
            groq_client = groq.AsyncGroq(api_key=self.groq_api_key)
            self.client = instructor.from_groq(groq_client)
            
        # STEP 0: Analyze User Request and determine which LLM to use (generalist LLM or tool-enabled for research LLM)
        # Print clear start marker for pipeline execution
        console.print("\n[bold blue]" + "="*50 + "\n" + 
                     "STARTING ROUTER STEP\n" + 
                     "="*50 + "[/bold blue]\n")

        # DEBUGGING statement
        if logger.getEffectiveLevel() == logging.DEBUG:
            panel = Panel.fit(
                Pretty(conversation_messages),
                style="router.debug", 
                border_style="router.debug.border",
                title="[bold]DEBUG: Input Messages[/bold]",
                title_align="left",
                subtitle="Router Debug | Conversation Analysis",
                subtitle_align="right",
                box=ROUNDED
            )            
            console.print(panel)

        # 1. Compile conversation
        cleaned_conversation_text = compile_conversation(conversation_messages)

        # DEBUGGING statement
        if logger.getEffectiveLevel() == logging.DEBUG:
            panel = Panel.fit(
                Pretty(cleaned_conversation_text),
                style="router.debug", 
                border_style="router.debug.border",
                title="[bold]DEBUG: Cleaned Text[/bold]",
                title_align="left",
                subtitle="Router Debug | Text Preprocessing",
                subtitle_align="right",
                box=ROUNDED
            )            
            console.print(panel)

        # 2. Build prompt
        ROUTER_PROMPT = """You are a task classification assistant named "Beacon". You must return valid JSON only.
        
        ## Steps

        1. Read the entire conversation carefully.
        
        2. Identify the last user message and infer the user task in context of the conversation history.
        
        3. Create a clear explanation of your reasoning for how you're understanding the user request. This should include your understanding of what the user is asking for and why you interpreted it that way.
        

        4. Determine the appropriate agent to handle the task:
        - Assign a router_decision of "RESEARCH_AGENT" for all tasks

        5. Summarize the conversation context that is relevant to the user's current task. Focus on key points from previous exchanges that directly relate to the current request.
        
        6. Rewrite the user's task as a complete, standalone query that explicitly includes all context necessary for understanding. Your "task" field should:
           - Incorporate relevant context from the conversation history
           - Explicitly mention all entities, locations, and topics
           - Resolve any pronouns (like "it", "they", "that region") to their specific referents
           - Be complete enough that someone with no knowledge of the previous conversation could understand it
           - Expand abbreviations to their full meaning where appropriate (e.g., "IHL" to "International Humanitarian Law")
           - Preserve the user's intent while making the task fully self-contained
                
        7. Return only the JSON object. Do not include any additional commentary or text.
        
        8. For the news_search_by_topic field, use full terms instead of acronyms (e.g., "International Armed Conflict" instead of "IAC") to improve search results.
        
        Your required output JSON must follow this schema exactly:
        {{
        "conversational_context": "string (summary of the conversation context synthesized)",
        "reasoning": "string (explanation of the decisions made when synthesizing the user task)",
        "router_decision": "string (must be RESEARCH_AGENT)",  
        "task": "string (the rewritten user task as a standalone, context-complete query)",
        "news_search_by_topic": "string (an optimized news search query for finding relevant articles). must be by keyword(s) and no longer than 3 words max. Always spell out acronyms in full (e.g., 'International Armed Conflict' instead of 'IAC')"
        }}
        
        ## Conversation
        {conversation}"""
        

#         4. Determine the appropriate agent to handle the task:
        #    - If the user task involves questions about Beacon, assign a router_decision of "BEACON_BASE_AGENT"
        #    - For all other tasks, assign a router_decision of "RESEARCH_AGENT"

        system_prompt = ROUTER_PROMPT.format(conversation=cleaned_conversation_text)

        # 3. Invoke the model using Groq with instructor
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # DEBUGGING statement
        if logger.getEffectiveLevel() == logging.DEBUG:
            formatted_text = Text(system_prompt, style="dim cyan", no_wrap=False, justify="left")

            panel = Panel(
                formatted_text,
                style="router.debug",
                border_style="router.debug.border",
                title="[bold]DEBUG: Router Prompt[/bold]",
                title_align="left",
                expand=True,
                subtitle="Router Debug | System Prompt",
                subtitle_align="right",
                box=ROUNDED
            )            
            console.print(panel)

        # 4. Use instructor to directly get a validated RouterResponse
        try:
            # Use instructor's patched client to get a typed response directly
            validated_response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                response_model=RouterResponse,
            )
            
            # For debugging, still show the raw JSON
            if logger.getEffectiveLevel() == logging.DEBUG:
                # Convert Pydantic model to dict for pretty printing
                response_dict = validated_response.model_dump()
                panel = Panel.fit(
                    Pretty(response_dict),
                    style="router.debug",
                    border_style="router.debug.border",
                    title="[bold]DEBUG: Router LLM Output[/bold]",
                    title_align="left",
                    subtitle="Router Debug | Validated Response",
                    subtitle_align="right",
                    box=ROUNDED
                )            
                console.print(panel)

            # Identify the last user message
            last_user_message = None
            for msg in reversed(conversation_messages):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content")
                    break

            # Ensure we have content
            last_user_message = last_user_message or "No user message found."

            # Extract router decision and user query from validated response
            reasoning = validated_response.reasoning
            router_decision = validated_response.router_decision
            conversational_context = validated_response.conversational_context
            task = validated_response.task
            news_search_by_topic = validated_response.news_search_by_topic

            # Construct the formatted text with line breaks
            formatted_text = Text()
            formatted_text.append("Last User Message in Convo:\n", style="bold #cba6f7")  # Use purple highlight color
            formatted_text.append(last_user_message + "\n\n", style="italic #89b4fa")     # Use info blue for user message
            formatted_text.append("Reasoning:\n", style="bold #cba6f7")                   # Purple for headings
            formatted_text.append(reasoning + "\n\n", style="router.process")             # Use new process color
            formatted_text.append("Router Decision:\n", style="bold #cba6f7")             # Purple for headings
            formatted_text.append(router_decision + "\n\n", style="bold router.highlight") # Orange for decision
            formatted_text.append("Conversation Context:\n", style="bold #cba6f7")        # Purple for headings
            formatted_text.append(conversational_context + "\n\n", style="router.process") # Process pink
            formatted_text.append("Rewritten User Task:\n", style="bold #cba6f7")         # Purple for headings
            formatted_text.append(task + "\n\n", style="router.highlight")                # Orange for task
            formatted_text.append("News Search Query:\n", style="bold #cba6f7")            # Purple for headings
            formatted_text.append(news_search_by_topic, style="router.success")               # Green for search query

            # INFO statement
            panel = Panel(
                formatted_text,
                style="router.info",
                border_style="router.info.border",
                title="[bold]INFO: Final Router Decision[/bold]",
                title_align="left",
                subtitle=f"Routing to: {router_decision}",
                subtitle_align="right",
                box=ROUNDED
            )
            console.print(panel)
        
            # Register end marker to be printed at end of execution
            console.print("\n[bold blue]" + "="*50 + "\n" +
                         "END OF ROUTER STEP\n" + 
                         "="*50 + "[/bold blue]\n")

            # Router response is now a validated Pydantic model
            return validated_response

        except Exception as e:
            logger.error(f"Router error: {e}")
            raise ValueError(f"Error getting structured response from router: {str(e)}") from e 