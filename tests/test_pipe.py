# tests/test_pipe.py

# RUN from root: python -m pytest -s tests/test_pipe.py
# Otherwise, run all tests with "python -m pytest" from the project root (pytest automatically discovers files named test_*.py or *_test.py in your tests/ folder and runs them)

import pytest
from rich.console import Console
from pipelines.beacon_openwebui_function_01_2025 import Pipe
from rich.markdown import Markdown
import os 

console = Console()

    # Define multiple test scenarios
    # Each scenario is a list of messages simulating a conversation flow.

test_scenarios = {
    "scenario_conflict_classification": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hello! How can I help you?"},
            {"role": "user", "content": "I'm curious about the conflict in Lebanon. Could you tell me more about it?"},
            {
                "role": "assistant",
                "content": "Sure! Are you interested in classification or specific details?",
            },
            {
                "role": "user",
                "content": "Specifically, I'd like to know if it's an International or Non-International Armed Conflict, and maybe some background.",
            },
        ],
    },
    # "scenario_single_user_message1": {
    #     "messages": [
    #         {"role": "user", "content": "Could you write me a poem about dogs?"},
    #     ],
    # },
    # "scenario_single_user_message2": {
    #     "messages": [
    #         {"role": "user", "content": "how many conflicts are found in west africa? "},
    #     ],
    # },
    # "scenario_single_user_message3": {
    #     "messages": [
    #         {"role": "user", "content": "how many conflicts in europe? "},
    #     ],
    # },
    #     "scenario_single_user_message4": {
    #     "messages": [
    #         {"role": "user", "content": "are there more conflicts in europe or west africa? "},
    #     ],
    # },
    # "scenario_switched_topic": {
    #     "messages": [
    #         {"role": "system", "content": "You are a helpful AI assistant."},
    #         {"role": "assistant", "content": "How can I help you today?"},
    #         {"role": "user", "content": "Tell me about the conflict in Ukraine."},
    #         {
    #             "role": "assistant",
    #             "content": "Sure. What aspect of the conflict?",
    #         },
    #         {
    #             "role": "user",
    #             "content": "Actually, never mind. I'd like some tips on home gardening instead.",
    #         },
    #     ],
    # },
    # "scenario_human_rights": {
    #     "messages": [
    #         {"role": "system", "content": "You are a helpful AI assistant."},
    #         {"role": "assistant", "content": "Welcome! How may I assist you?"},
    #         {
    #             "role": "user",
    #             "content": "Explain the Universal Declaration of Human Rights.",
    #         },
    #     ],
    # },
    # "scenario_irrelevant": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "Hello!"},
    #         {"role": "user", "content": "How do I fix my phone screen?"},
    #     ],
    # },

    "scenario_conflict_rulac_reference": {
        "messages": [
            {
                "role": "user",
                "content": "I want to see what RULAC says about the conflict in Syria.",
            },
        ],
        # Since it's specifically about conflict, we expect a conflict-related classification
    },

    # "scenario_conflict_israel_hamas": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant knowledgeable in armed conflict."},
    #         {"role": "assistant", "content": "Hello, I'm here to help."},
    #         {
    #             "role": "user",
    #             "content": "Could you tell me about the classification of the conflict between Israel and Hamas?",
    #         },
    #     ],
    #     # Another conflict question → "CONFLICT_OR_IHL"
    # },

    # "scenario_rulac_general": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant knowledgeable in armed conflict."},
    #         {"role": "assistant", "content": "Hello, I'm here to help."},
    #         {
    #             "role": "user",
    #             "content": "Could you tell me about RULAC?",
    #         },
    #     ],
    #     # Expecting a general classification to NOT query RULAC directly → "OTHER_SUBJECTS"
    # },

    # "scenario_health_advice": {
    #     "messages": [
    #         {"role": "system", "content": "You are a helpful AI assistant."},
    #         {"role": "assistant", "content": "Hello!"},
    #         {
    #             "role": "user",
    #             "content": "I've got a sore throat and headache. Any advice?",
    #         },
    #     ],
    #     # Not conflict or IHL → "OTHER_SUBJECTS"
    # },

    # "scenario_ihl_question": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant with expertise in IHL."},
    #         {"role": "assistant", "content": "How can I assist you today?"},
    #         {
    #             "role": "user",
    #             "content": "What's the difference between IHL and human rights law in armed conflicts?",
    #         },
    #     ],
    #     # Specifically about IHL → "CONFLICT_OR_IHL"
    # },
    #     # New / additional conflict or IHL scenarios

    # # 1) Specifically referencing RULAC
    # "scenario_conflict_rulac_reference": {
    #     "messages": [
    #         {"role": "system", "content": "You are a classification and rewriting assistant."},
    #         {"role": "assistant", "content": "Hello, how can I help you?"},
    #         {
    #             "role": "user",
    #             "content": "I want to see what RULAC says about the conflict in Syria.",
    #         },
    #     ],
    # },

    # # 2) Asking which IHL applies in a particular conflict
    # "scenario_ihl_applies_in_conflict": {
    #     "messages": [
    #         {"role": "system", "content": "You are an expert in armed conflict and IHL."},
    #         {"role": "assistant", "content": "Hello!"},
    #         {
    #             "role": "user",
    #             "content": "Which IHL provisions apply in the conflict in Yemen?",
    #         },
    #     ],
    # },

    # # 3) Asking about a particular non-state actor
    # "scenario_non_state_actor": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "How can I help you?"},
    #         {
    #             "role": "user",
    #             "content": "Which conflicts involve Boko Haram? How many are there?",
    #         },
    #     ],
    # },

    # # 4) Retrieving conflict data by State Actor
    # "scenario_conflicts_involving_russia": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "Welcome."},
    #         {
    #             "role": "user",
    #             "content": "What conflicts involve Russia as a party?",
    #         },
    #     ],
    # },

    # # 5) Retrieving classification data (e.g., Ukraine)
    # "scenario_conflict_classification_ukraine": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "Hello!"},
    #         {
    #             "role": "user",
    #             "content": "How is the conflict in Ukraine classified?",
    #         },
    #     ],
    # },

    # # 6) Retrieving IHL data for a specific conflict
    "scenario_conflict_ukraine_ihl": {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant with knowledge of IHL."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "How is the conflict in Ukraine classified and what IHL applies?",
            },
        ],
    },

    # # 7) Compare conflict data for multiple actors
    "scenario_compare_russia_usa_conflicts": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hey there."},
            {
                "role": "user",
                "content": "Are there more conflicts involving Russia or the United States as a state actor?",
            },
        ],
    },

    # # 8) Retrieving conflicts by classification (e.g., NIAC)
    # "scenario_conflicts_classified_as_niac": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant specialized in conflict data."},
    #         {"role": "assistant", "content": "Hi!"},
    #         {
    #             "role": "user",
    #             "content": "What conflicts are classified as NIAC? How many are there total?",
    #         },
    #     ],
    # },

    # # 9) Retrieving conflicts by geographic location
    # "scenario_conflicts_in_mali": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "Hello."},
    #         {
    #             "role": "user",
    #             "content": "How many conflicts are in Mali?",
    #         },
    #     ],
    # },

    # # 10) Parties to conflict in Ukraine
    # "scenario_conflict_parties_ukraine": {
    #     "messages": [
    #         {"role": "system", "content": "You are a specialized conflict assistant."},
    #         {"role": "assistant", "content": "Hi there!"},
    #         {
    #             "role": "user",
    #             "content": "What are the parties to the conflict in Ukraine?",
    #         },
    #     ],
    # },

    # # 11) Conflicts involving multiple countries
    # "scenario_conflict_european_state_actors": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant."},
    #         {"role": "assistant", "content": "How can I assist?"},
    #         {
    #             "role": "user",
    #             "content": "What conflicts involve state actors from Europe? How many of them are there in total?",
    #         },
    #     ],
    # },

    # # 12) Conflicts involving two specific state actors
    # "scenario_conflict_usa_russia": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant with knowledge of conflicts."},
    #         {"role": "assistant", "content": "Hello!"},
    #         {
    #             "role": "user",
    #             "content": "What conflicts involve both the USA and Russia?",
    #         },
    #     ],
    # },

    # # 13) Conflicts with a specific non-state actor and IHL
    # "scenario_conflict_isis_ihl": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant with knowledge of IHL."},
    #         {"role": "assistant", "content": "Hi!"},
    #         {
    #             "role": "user",
    #             "content": "How many conflicts involve ISIS as an actor? What is the applicable IHL for these conflicts?",
    #         },
    #     ],
    # },

    # # 14) Conflicts classified as military occupations
    # "scenario_conflict_military_occupations": {
    #     "messages": [
    #         {"role": "system", "content": "You are an AI assistant specialized in conflict classification."},
    #         {"role": "assistant", "content": "Hello."},
    #         {
    #             "role": "user",
    #             "content": "What conflicts are classified as military occupations? How many are there total?",
    #         },
    #     ],
    # },
}


@pytest.mark.asyncio
async def test_pipe_scenarios():
    """
    Example test function that checks multiple scenarios for your Pipe class.
    """
    # Instantiate Pipe
    pipe = Pipe(local_testing=True)

    # Mock user and request
    __user__ = {
        "id": "123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "tester",
    }
    __request__ = None  # Mock request (not used in this case)

    # A mock event emitter
    async def mock_event_emitter(event):
        console.log(f"[dim]Event emitted: {event}[/dim]")

    # Ensure the output directory exists
    output_dir = "tests/test_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Run each scenario
    for scenario_name, conversation_messages in test_scenarios.items():
        console.rule(f"[bold yellow]Testing scenario: {scenario_name}[/bold yellow]")

        body = {"messages": conversation_messages["messages"]}
        response = await pipe.pipe(
            body,
            __user__,
            __request__,
            mock_event_emitter,
            local_testing=True
        )

        console.log(f"[cyan]Response for scenario '{scenario_name}':[/cyan]")
        if response.startswith("#") or "**" in response or "*" in response:
            markdown_result = Markdown(response)
            console.print(markdown_result)
        else:
            console.log(response, style="dim")        
        
                # Save the response to a local file
        output_file_path = os.path.join(output_dir, f"{scenario_name}_output.txt")
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(response)

        console.rule("[bold green]End of scenario[/bold green]")

        # Optionally add asserts here for validation
        # Example:
        # assert "conflict" in response.lower(), "Expected 'conflict' in response"
