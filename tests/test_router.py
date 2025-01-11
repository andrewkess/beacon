# tests/test_router.py

# RUN from root: python -m pytest -s tests/test_router.py
# Otherwise, run all tests with "python -m pytest" from the project root (pytest automatically discovers files named test_*.py or *_test.py in your tests/ folder and runs them)

import pytest
from rich.console import Console
from pipelines.beacon_openwebui_function_01_2025 import Pipe

console = Console()

test_scenarios = {
    "scenario_conflict_classification": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hello! How can I help you?"},
            {"role": "user", "content": "I'm curious about the conflict in Somalia."},
            {
                "role": "assistant",
                "content": "Sure! Are you interested in classification or specific details?",
            },
            {
                "role": "user",
                "content": "Specifically, I'd like to know if it's an International or Non-International Armed Conflict, and maybe some background.",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },
    "scenario_single_user_message1": {
        "messages": [
            {"role": "user", "content": "Could you write me a poem about dogs?"},
        ],
        "expected_decision": "OTHER_SUBJECTS",
    },
    "scenario_single_user_message2": {
        "messages": [
            {"role": "user", "content": "how many conflicts are found in west africa? "},
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },
    "scenario_single_user_message3": {
        "messages": [
            {"role": "user", "content": "how many conflicts in europe? "},
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },
        "scenario_single_user_message4": {
        "messages": [
            {"role": "user", "content": "are there more conflicts in europe or west africa? "},
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },
    "scenario_switched_topic": {
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "assistant", "content": "How can I help you today?"},
            {"role": "user", "content": "Tell me about the conflict in Ukraine."},
            {
                "role": "assistant",
                "content": "Sure. What aspect of the conflict?",
            },
            {
                "role": "user",
                "content": "Actually, never mind. I'd like some tips on home gardening instead.",
            },
        ],
        "expected_decision": "OTHER_SUBJECTS",
    },
    "scenario_human_rights": {
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "assistant", "content": "Welcome! How may I assist you?"},
            {
                "role": "user",
                "content": "Explain the Universal Declaration of Human Rights.",
            },
        ],
        "expected_decision": "OTHER_SUBJECTS",
    },
    "scenario_irrelevant": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How do I fix my phone screen?"},
        ],
        "expected_decision": "OTHER_SUBJECTS",
    },
        # --------------- New / Expanded Scenarios ---------------

    "scenario_conflict_rulac_reference": {
        "messages": [
            {"role": "system", "content": "You are a classification and rewriting assistant."},
            {"role": "assistant", "content": "Hi there, how can I help you?"},
            {
                "role": "user",
                "content": "I want to see what RULAC says about the conflict in Syria.",
            },
        ],
        # Since it's specifically about conflict, we expect a conflict-related classification
        "expected_decision": "CONFLICT_OR_IHL",
    },

    "scenario_conflict_israel_hamas": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant knowledgeable in armed conflict."},
            {"role": "assistant", "content": "Hello, I'm here to help."},
            {
                "role": "user",
                "content": "Could you tell me about the classification of the conflict between Israel and Hamas?",
            },
        ],
        # Another conflict question → "CONFLICT_OR_IHL"
        "expected_decision": "CONFLICT_OR_IHL",
    },

    "scenario_rulac_general": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant knowledgeable in armed conflict."},
            {"role": "assistant", "content": "Hello, I'm here to help."},
            {
                "role": "user",
                "content": "Could you tell me about RULAC?",
            },
        ],
        # Expecting a general classification to NOT query RULAC directly → "OTHER_SUBJECTS"
        "expected_decision": "OTHER_SUBJECTS",
    },

    "scenario_health_advice": {
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "I've got a sore throat and headache. Any advice?",
            },
        ],
        # Not conflict or IHL → "OTHER_SUBJECTS"
        "expected_decision": "OTHER_SUBJECTS",
    },

    "scenario_ihl_question": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant with expertise in IHL."},
            {"role": "assistant", "content": "How can I assist you today?"},
            {
                "role": "user",
                "content": "What's the difference between IHL and human rights law in armed conflicts?",
            },
        ],
        # Specifically about IHL → "CONFLICT_OR_IHL"
        "expected_decision": "CONFLICT_OR_IHL",
    },
        # New / additional conflict or IHL scenarios

    # 1) Specifically referencing RULAC
    "scenario_conflict_rulac_reference": {
        "messages": [
            {"role": "system", "content": "You are a classification and rewriting assistant."},
            {"role": "assistant", "content": "Hello, how can I help you?"},
            {
                "role": "user",
                "content": "I want to see what RULAC says about the conflict in Syria.",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 2) Asking which IHL applies in a particular conflict
    "scenario_ihl_applies_in_conflict": {
        "messages": [
            {"role": "system", "content": "You are an expert in armed conflict and IHL."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "Which IHL provisions apply in the conflict in Yemen?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 3) Asking about a particular non-state actor
    "scenario_non_state_actor": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "How can I help you?"},
            {
                "role": "user",
                "content": "Which conflicts involve Boko Haram? How many are there?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 4) Retrieving conflict data by State Actor
    "scenario_conflicts_involving_russia": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Welcome."},
            {
                "role": "user",
                "content": "What conflicts involve Russia as a party?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 5) Retrieving classification data (e.g., Ukraine)
    "scenario_conflict_classification_ukraine": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "How is the conflict in Ukraine classified?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 6) Retrieving IHL data for a specific conflict
    "scenario_conflict_ukraine_ihl": {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant with knowledge of IHL."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "How is the conflict in Ukraine classified and what IHL applies?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 7) Compare conflict data for multiple actors
    "scenario_compare_russia_usa_conflicts": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hey there."},
            {
                "role": "user",
                "content": "Are there more conflicts involving Russia or the United States as a state actor?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 8) Retrieving conflicts by classification (e.g., NIAC)
    "scenario_conflicts_classified_as_niac": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant specialized in conflict data."},
            {"role": "assistant", "content": "Hi!"},
            {
                "role": "user",
                "content": "What conflicts are classified as NIAC? How many are there total?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 9) Retrieving conflicts by geographic location
    "scenario_conflicts_in_mali": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "Hello."},
            {
                "role": "user",
                "content": "How many conflicts are in Mali?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 10) Parties to conflict in Ukraine
    "scenario_conflict_parties_ukraine": {
        "messages": [
            {"role": "system", "content": "You are a specialized conflict assistant."},
            {"role": "assistant", "content": "Hi there!"},
            {
                "role": "user",
                "content": "What are the parties to the conflict in Ukraine?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 11) Conflicts involving multiple countries
    "scenario_conflict_european_state_actors": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "assistant", "content": "How can I assist?"},
            {
                "role": "user",
                "content": "What conflicts involve state actors from Europe? How many of them are there in total?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 12) Conflicts involving two specific state actors
    "scenario_conflict_usa_russia": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant with knowledge of conflicts."},
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "user",
                "content": "What conflicts involve both the USA and Russia?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 13) Conflicts with a specific non-state actor and IHL
    "scenario_conflict_isis_ihl": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant with knowledge of IHL."},
            {"role": "assistant", "content": "Hi!"},
            {
                "role": "user",
                "content": "How many conflicts involve ISIS as an actor? What is the applicable IHL for these conflicts?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },

    # 14) Conflicts classified as military occupations
    "scenario_conflict_military_occupations": {
        "messages": [
            {"role": "system", "content": "You are an AI assistant specialized in conflict classification."},
            {"role": "assistant", "content": "Hello."},
            {
                "role": "user",
                "content": "What conflicts are classified as military occupations? How many are there total?",
            },
        ],
        "expected_decision": "CONFLICT_OR_IHL",
    },
}

@pytest.mark.asyncio
async def test_router_function():
    """
    A test function that sets up multiple conversations,
    invokes the router for each scenario, and verifies the decision.
    """
    pipe = Pipe(local_testing=True)
    scenario_results = []

    for scenario_name, scenario_data in test_scenarios.items():
        messages = scenario_data["messages"]
        expected_decision = scenario_data["expected_decision"]

        # Identify last user message for logging
        last_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "user"),
            None
        )

        # Invoke the router
        router_response = await pipe.router(messages)
        actual_decision = router_response.router_decision
        rewritten_query = router_response.user_query

        # Logging with Rich
        console.rule(f"[bold yellow]Scenario: {scenario_name}[/bold yellow]")
        console.log(f"Last Convo Message: [cyan]{last_user_message}[/cyan]")
        console.log(f"Expected Decision: [red]{expected_decision}[/red]")
        console.log(f"Actual Decision: [green]{actual_decision}[/green]")
        console.log(f"Rewritten Query: [magenta]{rewritten_query}[/magenta]")

        # Perform the assert
        assert actual_decision == expected_decision, (
            f"For {scenario_name}, expected decision '{expected_decision}' "
            f"but got '{actual_decision}'."
        )

        # Collect data for final summary
        scenario_results.append({
            "scenario": scenario_name,
            "expected": expected_decision,
            "actual": actual_decision,
            "user_query": rewritten_query,
        })

    # Final summary
    console.rule("[bold green]FINAL ROUTER TEST SUMMARY[/bold green]")
    for result in scenario_results:
        console.log(
            f"[bold cyan]{result['scenario']}[/bold cyan] => "
            f"Expected: [bold red]{result['expected']}[/bold red], "
            f"Actual: [bold green]{result['actual']}[/bold green], "
            f"Rewritten Query: [italic]{result['user_query']}[/italic]"
        )

    # Optional additional cross-check
    # e.g., ensure no scenario returned an empty user_query
    for result in scenario_results:
        assert result["user_query"], (
            f"Scenario {result['scenario']} returned an empty user_query!"
        )
