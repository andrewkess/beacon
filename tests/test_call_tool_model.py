# tests/test_call_tool_model.py

# RUN from root: python -m pytest -s tests/test_call_tool_model.py
# Otherwise, run all tests with "python -m pytest" from the project root (pytest automatically discovers files named test_*.py or *_test.py in your tests/ folder and runs them)

import pytest
from rich.console import Console

from pipelines.beacon_openwebui_function_01_2025 import Pipe
from fastapi import Request  # Mock for Request

console = Console()

@pytest.mark.asyncio
async def test_call_tool_model_scenarios():
    """
    Integration test for call_tool_model with multiple test cases.
    Focuses on comparing rewritten_query vs. tool call query.
    """
    # Initialize the Pipe instance
    pipe = Pipe(local_testing=True)  # Adjust this based on how you initialize Pipe

    # Define test cases (rewritten_query inputs)
    test_cases = [
        "What conflicts involve state actors in the Middle East? How many total?",
        "Classify the conflict between Israel and Hamas under IHL.",
        "Provide an overview of IHL applicable in the conflict in Yemen.",
        "List all ongoing armed conflicts in Africa.",
        "What are the legal classifications of the conflict in Ukraine?",
        "Which IHL laws apply to non-state actors in Syria?",
        "What conflicts involve Sudan as a state actor?",
        "Classify the conflict in Somalia and provide the relevant IHL.",
    ]

    # A mock event emitter
    async def mock_event_emitter(event):
        console.log(f"[dim]Event emitted: {event}[/dim]")

    # Run each test case
    for rewritten_query in test_cases:
        # Call the tool model
        tool_calls = await pipe.call_tool_model(
            rewritten_query=rewritten_query,
            __event_emitter__=mock_event_emitter  # Disable event emitter for test
        )

        # Print comparison of rewritten query vs tool call query
        print("\n[TEST CASE]")
        if tool_calls:
            for call in tool_calls:
                print(f"Tool Name: {call['name']}")
                print(f"Initial Query: {rewritten_query}")
                print(f"Tool Call Query: {call['args']['query']}")
        else:
            print("No tool calls were generated.")

        # Assertions
        assert tool_calls, f"No tool calls generated for query: {rewritten_query}"
        assert tool_calls[0]["args"]["query"], "Tool call query is missing."

