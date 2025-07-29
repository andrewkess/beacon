import asyncio
import logging
import json
import os
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.style import Style
from rich.theme import Theme
from rich.pretty import Pretty
from rich.box import ROUNDED
import coloredlogs
import groq
import instructor

# Import Router directly instead of Pipe
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from agents.router import Router

# Import scenarios from the Python module instead of JSON
from tests.validated.router_test_scenarios import TEST_SCENARIOS, PRIORITY_SCENARIO

# Define custom theme for rich console output - must match router.py
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
    "router.highlight": "bold #fab387",      # Orange for highlights
    
    # Test theme - complementary to the modern palette
    "test.header": "white on #45475a",       # Darker gray for headers
    "test.header.border": "#cba6f7",         # Purple border matching router theme
    "test.info": "white on #7f849c",         # Medium gray for info
    "test.info.border": "#89b4fa",           # Blue border
    "test.result": "white on #585b70",       # Slate color for results
    "test.result.border": "#a6e3a1"          # Green border for results
})

# Create a console for rich output formatting with theme
console = Console(theme=custom_theme)

# Configure logging (should match main module's configuration)
logger = logging.getLogger("BeaconTestRouter")
# Set the logging level to DEBUG
logger.setLevel(logging.INFO)

# Test function for the router to run standalone
# This function is used to test the router by itself, without the rest of the pipeline
# It is used to test the router's ability to make decisions based on the conversation history
# Now using instructor-based Groq integration for direct Pydantic validation

def test_router_function(max_scenarios=1, test_one=True):
    """
    A test function that sets up multiple conversations,
    invokes the router for each scenario, and logs a final summary.
    
    Args:
        max_scenarios: Maximum number of scenarios to test (default: 1)
        test_one: When True, only tests the WEB_SEARCH_SCENARIO (default: True)
    """
    # Create a router instance directly
    router_instance = Router()

    # Use imported TEST_SCENARIOS directly instead of loading from JSON
    if test_one:
        # When test_one is True, only use the WEB_SEARCH_SCENARIO
        test_scenarios = {"priority_scenario": PRIORITY_SCENARIO}
        console.print(Panel(
            "[bold]Testing only PRIORITY SCENARIO[/bold]",
            style="test.info",
            border_style="test.info.border",
            title="[bold]INFO: Test Configuration[/bold]",
            title_align="left",
            box=ROUNDED
        ))
    else:
        # Use all scenarios
        test_scenarios = TEST_SCENARIOS
        logger.info(f"Loaded {len(test_scenarios)} test scenarios from Python module")
        
        # Limit the number of scenarios if max_scenarios is set
        if max_scenarios and len(test_scenarios) > max_scenarios:
            original_count = len(test_scenarios)
            # Take only the first max_scenarios scenarios
            limited_scenarios = dict(list(test_scenarios.items())[:max_scenarios])
            test_scenarios = limited_scenarios
            logger.info(f"Limited testing to {max_scenarios} scenarios out of {original_count}")
            console.print(Panel(
                f"[bold]Testing limited to {max_scenarios} scenarios out of {original_count}[/bold]",
                style="test.info",
                border_style="test.info.border",
                title="[bold]INFO: Test Configuration[/bold]",
                title_align="left",
                box=ROUNDED
            ))

    async def async_test_router():
        """
        Asynchronous test function that loops through scenarios,
        calls the router, and logs results.
        """
        # Collect results for final summary
        scenario_results = []

        # Loop over each scenario
        for scenario_name, conversation_messages in test_scenarios.items():
                        # Print scenario info
            console.print(Panel(
                f"[bold]Starting test for scenario: {scenario_name}[/bold]",
                style="test.info", 
                border_style="test.info.border",
                title="[bold]INFO: Test Execution[/bold]",
                title_align="left",
                subtitle="Router Test",
                subtitle_align="right",
                box=ROUNDED
            ))

            # Identify the last user message
            last_user_message = None
            for msg in reversed(conversation_messages):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content")
                    break

            # Invoke the router directly instead of through pipe
            # Router now uses instructor for direct Pydantic validation
            router_response = await router_instance.route(conversation_messages)

            # Store a summary for final output
            scenario_results.append(
                {
                    "scenario": scenario_name,
                    "last_user_message": last_user_message,
                    "reasoning": router_response.reasoning,
                    "decision": router_response.router_decision,
                    "conversational_context": router_response.conversational_context,
                    "task": router_response.task,
                    "news_search_by_topic": router_response.news_search_by_topic,
                }
            )

        # Generate and display formatted summary in one console output
        logger.info("\n=== FINAL TEST SUMMARY ===")
        
        console.print(Panel(
            "[bold]Test Summary[/bold]",
            style="test.info", 
            border_style="test.info.border",
            title="[bold]INFO: Final Results[/bold]",
            title_align="left",
            subtitle=f"Test Completed: {len(scenario_results)} Scenario(s)",
            subtitle_align="right",
            box=ROUNDED
        ))

        panels = []  # Store all panels to display together

        for result in scenario_results:
            scenario_name = result["scenario"]
            last_user_message = result["last_user_message"]
            reasoning = result["reasoning"]
            decision = result["decision"]
            conversational_context = result["conversational_context"]
            task = result["task"]
            news_search_by_topic = result["news_search_by_topic"]

            # Construct formatted text
            formatted_text = Text()
            formatted_text.append("Scenario:", style="bold #cba6f7")  # Purple heading
            formatted_text.append(f" {scenario_name}\n\n", style="bold router.highlight")  # Orange highlight
            formatted_text.append("Last User Message in Convo:\n", style="bold #cba6f7")   # Purple heading
            formatted_text.append(last_user_message + "\n\n", style="italic #89b4fa")      # Blue for message
            formatted_text.append("Reasoning:\n", style="bold #cba6f7")                    # Purple heading
            formatted_text.append(reasoning + "\n\n", style="router.process")              # Pink for reasoning
            formatted_text.append("Router Decision:\n", style="bold #cba6f7")              # Purple heading
            formatted_text.append(decision + "\n\n", style="bold router.highlight")        # Orange for decision
            formatted_text.append("Conversation Context:\n", style="bold #cba6f7")         # Purple heading
            formatted_text.append(conversational_context + "\n\n", style="router.process") # Pink for context
            formatted_text.append("Rewritten User Task:\n", style="bold #cba6f7")          # Purple heading
            formatted_text.append(task + "\n\n", style="bold router.success")               # Green for task (changed from router.highlight)
            formatted_text.append("News Search Query:\n", style="bold #cba6f7")             # Purple heading
            formatted_text.append(news_search_by_topic, style="router.success")                # Green for search query

            # Create panel for this scenario
            panel = Panel(
                formatted_text,
                style="test.result",
                border_style="test.result.border",
                title=f"[bold]RESULT: Router Analysis for {scenario_name}[/bold]",
                title_align="left",
                subtitle=f"Decision: {decision}",
                subtitle_align="right",
                box=ROUNDED
            )

            panels.append(panel)  # Add panel to list

        # Print all panels together in a single console output
        console.print(*panels)


    # Run the async part
    asyncio.run(async_test_router()) 

# Execute the test function when running the script directly
if __name__ == "__main__":
    
    # Configure logging for standalone execution
    coloredlogs.install(
        logger=logger,
        level="INFO",
        isatty=True,
        fmt="%(asctime)s [%(levelname)s] %(message)s",
    )
    # test_one = True
    test_one = False
    max_scenarios = None

    scenario_message = "Testing PRIORITY SCENARIO" if test_one else f"max {max_scenarios if max_scenarios else 'all'} scenarios"
    console.print(Panel(
        f"[bold]Running Router Test Standalone[/bold]\n{scenario_message}", 
        style="test.header",
        border_style="test.header.border",
        title="[bold]TEST: Router Test[/bold]",
        title_align="left",
        box=ROUNDED
    ))
    test_router_function(max_scenarios, test_one) 
    console.print(Panel(
        "[bold]Router Test Standalone Complete[/bold]", 
        style="test.header",
        border_style="test.header.border",
        title="[bold]TEST: Execution Complete[/bold]",
        title_align="left",
        box=ROUNDED
    ))
