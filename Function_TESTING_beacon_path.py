"""
requirements: coloredlogs==15.0.1, pydantic==2.10.3, fastapi==0.115.6, asyncio, requests==2.32.3, sys
"""
from pydantic import BaseModel, Field
from fastapi import Request
import asyncio
import os
import json
import requests
import coloredlogs
import logging


from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
import os
from typing import Union, Generator, Iterator
from typing import AsyncGenerator
# // LOGGING //
import sys

# this way was working in an older version that used pipelines version (but the path would need to change)
# from beacon_reqs_agent_files.utils.logging import setup_logging



import os
import sys

# Debugging: print current working directory and sys.path
print("DEBUG: Current working directory:", os.getcwd())
print("DEBUG: sys.path:", sys.path)
print("DEBUG: Checking if /app/beacon_code/helpers/helper_functions.py exists:", 
      os.path.exists("/app/beacon_code/helpers/helper_functions.py"))

if os.path.exists("/app/beacon_code/helpers/helper_functions.py"):
    # Ensure that /app is in sys.path so that the beacon_code package can be found.
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")
        print("DEBUG: /app added to sys.path:", sys.path)
        
    try:
        from beacon_code.helpers.helper_functions import load_template_from_github  # type: ignore
        print("Running in container mode: using beacon_code version")
    except Exception as e:
        print("DEBUG: Error importing beacon_code.helpers.helper_functions:", e)
        raise
else:
    try:
        from helpers.helper_functions import load_template_from_github
        print("Running in local mode: using local version")
    except Exception as e:
        print("DEBUG: Error importing helpers.helper_functions:", e)
        raise


# how do i get this code path tho locally, if not running in the openweb container?
# here is the local path:
# /home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/helpers/helper_functions.py

# Configure logging (should be set to INFO unless DEBUG needed)
logger = logging.getLogger("Beacon")
coloredlogs.install(
    logger=logger,
    level="DEBUG",
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
)
# Initialize Rich Console
console = Console()


# // PIPELINE //

class Pipe:

    # Initialize pipeline (ie. once at start) to define the neo4j URL and the LLMs to use
    def __init__(self, local_testing: bool = False):
        self.local_testing = local_testing  # Set local testing flag


    # Main execution logic that starts and ends full pipeline, messages are sent as 'body' input from the OPENWEBUI app and/or through local testing
    # For now, we are just returning a string to display in OPENWEBUI chatbox 
    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __request__: Request,
        __event_emitter__=None,
        local_testing: bool = False,
    ) -> Union[str, Generator, Iterator, AsyncGenerator]:


        # Extract messages from body input
        logger.debug("Full conversation data input:\n%s", json.dumps(body, indent=2))
        messages = body.get("messages", [])
        logger.debug("All messages extracted from conversation:\n%s", json.dumps(messages, indent=2))

        #Define and emit event
        eventMessageUI = "Testing beacon function..."
        # Emit event for UI (user facing)
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": eventMessageUI,
                        "done": False,
                    },
                }
            )
        # Emit event for logs (developer facing)
        panel = Panel.fit(eventMessageUI, style="black on yellow", border_style="yellow")       
        # Print nicely formatted box to console
        console.print(panel)



        #Try and call function

        # GROUP ALL TOOL MESSAGE CITATION COUNTS to display final citation matches in UI 
        print(f"DEBUG: Calling function")

        stringTextToReturn = load_template_from_github("https://raw.githubusercontent.com/andrewkess/beacon/main/prompts/final_beacon_base_model_prompt.txt")


        # Emit event for UI (user facing)
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": stringTextToReturn,
                        "done": True,
                    },
                }
            )
        # Emit event for logs (developer facing)
        panel = Panel.fit(eventMessageUI, style="black on yellow", border_style="yellow")       
        # Print nicely formatted box to console
        console.print(panel)

        # FINAL ANSWER sent to OPENWEBUI
        return stringTextToReturn 




# TESTING SUITE



import asyncio
import json

# Define multiple test scenarios
# Each scenario is a list of messages simulating a conversation flow.
test_scenarios = {
    "scenario_single_user_message1": [
        # Only a single user message, no system/assistant context
        {"role": "user", "content": "Could you write me a poem about dogs?"},
                {
            "role": "assistant",
            "content": "Dogs are blue, roses are red, don't be sad, dogs help you.",
        },
        {"role": "user", "content": "Could you rewrite that,  but just change the flower to violets? Sign it with today's date and time"},
    ],
    # "scenario_single_user_message2": [
    #     # Only a single user message, no system/assistant context
    #     {"role": "user", "content": "is france a state party to conflict?"},
    # ],
   
}


def test_pipe():
    # Initialize the Pipe
    pipe = Pipe(local_testing=True)

    __user__ = {
        "id": "123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "tester",
    }
    __request__ = None  # Mock request (not used in this case)

    async def mock_event_emitter(event):
        """
        Logs an event at the INFO level and displays UI event description in a yellow box using Rich.
        """
        # description = event.get("data", {}).get("description", "No description available")  # Safely extract description
        
        # panel = Panel.fit(description, style="black on yellow", border_style="yellow")
        
        # # Print nicely formatted box to console
        # console.print(panel)


    async def run_tests():
        # Loop over each scenario
        for scenario_name, conversation_messages in test_scenarios.items():
            print(f"\n=== Testing scenario: {scenario_name} ===")

            # Prepare the body with the full conversation
            body = {"messages": conversation_messages}

            # Invoke pipe.pipe
            response = await pipe.pipe(
                body, __user__, __request__, mock_event_emitter, local_testing=True
            )


            # final_answer = ""
            # print("Streaming response tokens...")
            # for token in response:
            #     # print(token, end="")
            #     final_answer += token

            # Now display the final answer as a Markdown element using a Rich Panel.
            panel = Panel(
                Markdown(response),
                style="white on black",  # White text on black background for contrast
                border_style="purple3",
                title="Final LLM Answer",
                title_align="left",
            )
            console.print(panel)


            print("\nTest complete.")

            # print(f"\n=== Response for scenario '{scenario_name}':\n{response}\n")
            # print("===" * 10)

    # Run the async test sequence
    asyncio.run(run_tests())

# Run the test
if __name__ == "__main__":
    test_pipe()