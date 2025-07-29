import asyncio
import json
import logging
import os
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import coloredlogs
from rich.pretty import Pretty

# Import Pipe from the main module
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from OPENWEBUI_functions.DRAGON_Beacon_v1 import Pipe

# Import scenarios from the Python module
from tests.validated.router_test_scenarios import TEST_SCENARIOS, PRIORITY_SCENARIO

# Create a console for rich output formatting
console = Console()

# Configure logging (should match main module's configuration)
logger = logging.getLogger("BeaconTest")

async def test_router_and_tools_function(pipe_instance=None, max_scenarios=1, test_one=True):
    """
    A test function that sets up multiple conversations,
    invokes the router for each scenario, tests the tool calling model based on router decisions,
    and logs a comprehensive summary of the entire process.
    
    Args:
        pipe_instance: An initialized instance of the Pipe class. If None, one will be created.
        max_scenarios: Maximum number of scenarios to test (default: 1)
        test_one: When True, only tests the PRIORITY_SCENARIO (default: True)
    """
    # Ensure json is available throughout this function
    import json
    
    # Create a pipe instance if not provided
    if pipe_instance is None:
        pipe_instance = Pipe(local_testing=True)

    # Use the scenario logic from test_router.py
    if test_one:
        # When test_one is True, only use the PRIORITY_SCENARIO
        test_scenarios = {"priority_scenario": PRIORITY_SCENARIO}
        logger.info("Testing only PRIORITY SCENARIO")
        console.print("[yellow]Testing only PRIORITY SCENARIO[/yellow]")
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
            console.print(f"[yellow]Testing limited to {max_scenarios} scenarios out of {original_count}[/yellow]")

    # Collect results for final summary
    scenario_results = []

    # Loop over each scenario
    for scenario_name, conversation_messages in test_scenarios.items():
        logger.info(f"\n=== Testing scenario: {scenario_name} ===")

        # Identify the last user message
        last_user_message = None
        for msg in reversed(conversation_messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content")
                break

        # Step 1: Invoke the router
        router_result = await pipe_instance.router.route(conversation_messages)
        router_decision = router_result.router_decision
        rewritten_task = router_result.task
        conversation_context = router_result.conversational_context
        reasoning = router_result.reasoning
        news_search_by_topic = router_result.news_search_by_topic

        # Display router results
        router_panel = Panel(
            f"Router Decision: {router_decision}\nRewritten Task: {rewritten_task}\nReasoning: {reasoning[:100]}...\nConversation Context: {conversation_context[:100]}...\nNews Search Query: {news_search_by_topic if news_search_by_topic else 'None'}...",
            style="white on blue",
            border_style="blue",
            title=f"[Router Results for '{scenario_name}']",
            title_align="left"
        )
        console.print(router_panel)

        # Step 2: Based on router decision, test the appropriate next step
        tool_calls = []
        tool_outputs = []
        
        if router_decision == "RESEARCH_AGENT":
            # Test the tool calling model
            console.print(Panel("Testing Tool Calling Model...", style="black on yellow"))
            
            try:
                # Call the tool model with the rewritten task and conversation context from the router
                # The tool_outputs will now be a list of dictionaries with tool_name, tool_call_id, and content
                tool_output_list = await pipe_instance.handle_tool_query(rewritten_task, conversation_context, news_search_by_topic)
                
                # Log the actual structure of tool_outputs for debugging
                logger.debug(f"Tool output list type: {type(tool_output_list)}")
                if tool_output_list:
                    logger.debug(f"First tool output keys: {list(tool_output_list[0].keys()) if isinstance(tool_output_list[0], dict) else 'Not a dict'}")
                
                # Process each tool output in the list
                for output_item in tool_output_list:
                    if isinstance(output_item, dict):

                        # debug shape of output_item
                        # logger.debug(f"Tool output item shape: {output_item}")
                        # return

                        # Extract tool call information
                        tool_name = output_item.get("tool_name", "unknown")
                        tool_call_id = output_item.get("tool_call_id", "unknown")
                        content = output_item.get("content", "")
                        
                        # Extract tool parameters from the content if it's a RULAC_TOOL_RESULT
                        tool_args = {}
                        if isinstance(content, dict) and "tool_use_metadata" in content:
                            metadata = content.get("tool_use_metadata", {})
                            tool_args = metadata.get("tool_params", {})
                        # If args are available directly in the output_item, use those
                        elif "args" in output_item:
                            tool_args = output_item.get("args", {})
                        
                        # Add to tool_calls list for our summary with the extracted args
                        tool_calls.append({
                            "name": tool_name,
                            "id": tool_call_id,
                            "args": tool_args
                        })
                        
                        # Add content to tool_outputs list for our summary
                        if content:
                            # Handle if content is a dict with the new RULAC_TOOL_RESULT format
                            if isinstance(content, dict):
                                logging.debug(f"Content is a dictionary with keys: {content.keys()}")
                                
                                # Pretty print the dict content for better debugging
                                logger.debug(f"Content (pretty printed):\n{json.dumps(content, indent=2, ensure_ascii=False)}")
                                
                                # Process for RULAC_TOOL_RESULT format
                                if "content" in content and "citations" in content:
                                    logger.debug(f"Found RULAC_TOOL_RESULT format with content and citations")
                                    
                                    # Add content to tool outputs
                                    if "summary" in content:
                                        tool_outputs.append(f"Summary: {content['summary']}")
                                    
                                    if "conflict_details" in content:
                                        conflict_count = len(content.get('conflict_details', []))
                                        tool_outputs.append(f"Found {conflict_count} conflict details")
                                    
                                    # Add citation information
                                    citations = content.get("citations", [])
                                    citation_count = len(citations)
                                    logger.debug(f"Found {citation_count} citations")
                                    
                                    # Show first few citations
                                    if citation_count > 0:
                                        tool_outputs.append(f"Number of citations: {citation_count}")
                                        for i, citation in enumerate(citations[:3]):
                                            title = citation.get("title", "No title")
                                            url = citation.get("url", "No URL")
                                            tool_outputs.append(f"Citation {i+1}: {title} - {url}")
                                        if citation_count > 3:
                                            tool_outputs.append(f"... and {citation_count - 3} more citations")
                                else:
                                    # For other dictionary formats
                                    tool_outputs.append(f"Dictionary content with keys: {', '.join(content.keys())}")
                            else:
                                # Content is a string, not a dict
                                logging.debug(f"Content is a string with length: {len(str(content))}")
                                
                                # String content
                                if len(str(content)) > 500:
                                    tool_outputs.append(f"{str(content)[:500]}...")
                                else:
                                    tool_outputs.append(str(content))
                    else:
                        logger.warning(f"Unexpected tool output item type: {type(output_item)}")
                
                # Display tool results
                tool_panel_content = Text()
                tool_panel_content.append("Tool Calls:\n", style="bold underline")
                
                if tool_calls:
                    for i, tool_call in enumerate(tool_calls, 1):
                        tool_panel_content.append(f"\nTool Call {i}:\n", style="bold")
                        tool_panel_content.append(f"Name: {tool_call['name']}\n")
                        if 'id' in tool_call:
                            tool_panel_content.append(f"ID: {tool_call['id']}\n")
                else:
                    tool_panel_content.append("No tool calls found in output\n")
                    # Show raw output info
                    tool_panel_content.append(f"Raw output count: {len(tool_output_list)}\n")
                    if tool_output_list:
                        for i, out in enumerate(tool_output_list):
                            tool_panel_content.append(f"Output {i} type: {type(out).__name__}\n")
                            if isinstance(out, dict):
                                tool_panel_content.append(f"Output {i} keys: {list(out.keys())}\n")
                
                tool_panel = Panel(
                    tool_panel_content,
                    style="white on green",
                    border_style="green",
                    title="[Tool Model Results]",
                    title_align="left"
                )
                console.print(tool_panel)
                
                # If there are tool outputs, display them
                if tool_outputs:
                    output_panel_text = []
                    for i, output in enumerate(tool_outputs):
                        # Ensure we have a string
                        output_str = str(output) if output is not None else "None"
                        # Get a preview with proper truncation
                        preview = output_str[:200] + "..." if len(output_str) > 200 else output_str
                        output_panel_text.append(f"Output {i+1}:\n{preview}")
                    
                    output_panel = Panel(
                        "\n\n".join(output_panel_text),
                        style="white on cyan",
                        border_style="cyan",
                        title="[Tool Outputs (truncated)]",
                        title_align="left"
                    )
                    console.print(output_panel)
                else:
                    console.print(Panel("No tool outputs found", style="white on red"))
                
            except Exception as e:
                console.print(f"[bold red]Error testing tool model:[/bold red] {str(e)}")
                import traceback
                console.print(traceback.format_exc())
                tool_calls = [{"error": str(e)}]
        
        # Store results for final summary
        scenario_results.append({
            "scenario": scenario_name,
            "last_user_message": last_user_message,
            "router_decision": router_decision,
            "rewritten_task": rewritten_task,
            "reasoning": reasoning,
            "conversational_context": conversation_context,
            "news_search_by_topic": news_search_by_topic,
            "tool_calls": tool_calls,
            "tool_outputs_count": len(tool_outputs)
        })

    # Generate and display formatted summary
    logger.info("\n=== FINAL TEST SUMMARY ===")
    
    summary_table = Table(title="Router and Tool Testing Summary")
    summary_table.add_column("Scenario", style="cyan")
    summary_table.add_column("Router Decision", style="green")
    summary_table.add_column("Tool Calls", style="yellow")
    
    for result in scenario_results:
        if result['router_decision'] == "RESEARCH_AGENT":
            tool_calls_summary = f"{len(result['tool_calls'])} call(s)"
            if len(result['tool_calls']) > 0:
                # Add summary of first tool call
                tool_call = result['tool_calls'][0]
                tool_name = tool_call.get('name', 'unknown')
                tool_calls_summary += f"\nFirst: {tool_name}"
                # Add more if there are more
                if len(result['tool_calls']) > 1:
                    tool_calls_summary += f" (+{len(result['tool_calls'])-1} more)"
        else:
            tool_calls_summary = "N/A (General LLM used)"
        
        summary_table.add_row(
            result['scenario'], 
            result['router_decision'],
            tool_calls_summary
        )
    
    console.print(summary_table)
    
    # Print detailed results for each scenario
    for result in scenario_results:
        detailed_text = Text()
        detailed_text.append(f"Last User Message: {result['last_user_message']}\n\n")
        detailed_text.append(f"Router Decision: {result['router_decision']}\n")
        detailed_text.append(f"Rewritten Task: {result['rewritten_task']}\n")
        detailed_text.append(f"News Search Query: {result['news_search_by_topic'] if result['news_search_by_topic'] else 'None'}\n\n")
        detailed_text.append(f"Conversational Context: {result['conversational_context']}\n\n")
        detailed_text.append(f"Router Reasoning: {result['reasoning']}\n\n")
        
        # Enhanced tool calls display with names and parameters
        if result['router_decision'] == "RESEARCH_AGENT":
            detailed_text.append(f"Tool Calls: {len(result['tool_calls'])}\n")
            
            if result['tool_calls']:
                for i, call in enumerate(result['tool_calls']):
                    # Debug: Print the full call structure
                    # logger.debug(f"Tool Call {i+1} structure: {json.dumps(call, indent=2)}")
                    
                    detailed_text.append(f"\n  Tool Call {i+1}: ", style="bold")
                    detailed_text.append(f"{call.get('name', 'Unknown')}\n")
                    if 'id' in call:
                        detailed_text.append(f"  ID: {call.get('id', 'Unknown')}\n")
                    
                    # Add display of arguments
                    if 'args' in call:
                        detailed_text.append(f"  Arguments:\n")
                        args = call.get('args', {})
                        for arg_name, arg_value in args.items():
                            # Format the argument value for display
                            if isinstance(arg_value, list):
                                if len(arg_value) > 0:
                                    arg_display = f"[{', '.join(repr(v) for v in arg_value[:3])}{'...' if len(arg_value) > 3 else ''}]"
                                else:
                                    arg_display = "[]"
                            elif isinstance(arg_value, dict):
                                arg_display = "{...}" if arg_value else "{}"
                            elif isinstance(arg_value, str) and len(arg_value) > 100:
                                arg_display = f'"{arg_value[:100]}..."'
                            else:
                                arg_display = repr(arg_value)
                            detailed_text.append(f"    {arg_name}: {arg_display}\n")
                    
                    detailed_text.append("\n")
            
            detailed_text.append(f"\nTool Outputs: {result['tool_outputs_count']}\n")
        else:
            detailed_text.append("Tool Calls: N/A\n")
            detailed_text.append("Tool Outputs: N/A\n")
        
        detailed_panel = Panel(
            detailed_text,
            title=f"Detailed Results: {result['scenario']}",
            style="white on black",
            border_style="purple"
        )
        console.print(detailed_panel)

# Main function to run the test independently
if __name__ == "__main__":
    # Configure logging for standalone execution
    coloredlogs.install(
        logger=logger,
        level="DEBUG",  # Change to DEBUG to see more detailed logs
        isatty=True,
        fmt="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    # Set default parameters
    test_one = True
    max_scenarios = 3
    
    # Parse command line arguments if needed
    parser = argparse.ArgumentParser(description='Test router and tools with various scenarios')
    parser.add_argument('--all', action='store_true', help='Test all scenarios instead of just priority scenario')
    parser.add_argument('--max', type=int, default=3, help='Maximum number of scenarios to test')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    if args.all:
        test_one = False
    
    max_scenarios = args.max
    
    # Set debug level if requested
    if args.debug:
        coloredlogs.install(
            logger=logger,
            level="DEBUG",
            isatty=True,
            fmt="%(asctime)s [%(levelname)s] %(message)s",
        )
        logger.debug("Debug logging enabled")
    
    scenario_message = "Testing PRIORITY SCENARIO" if test_one else f"max {max_scenarios if max_scenarios else 'all'} scenarios"
    console.print(Panel(
        f"Running Router and Tools Test ({scenario_message})", 
        style="white on blue"
    ))
    
    asyncio.run(test_router_and_tools_function(None, max_scenarios, test_one))
    
    console.print(Panel("Router and Tools Test Complete", style="white on blue")) 