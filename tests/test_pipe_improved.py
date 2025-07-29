import pytest
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from pipelines.beacon_openwebui_function_01_2025 import Pipe

console = Console()

@dataclass
class TestResult:
    """Data class to store test results"""
    scenario_name: str
    success: bool
    duration: float
    error: str = None
    response: str = None
    expected_content: List[str] = None
    actual_content: List[str] = None

class TestConfig:
    """Configuration class for test settings"""
    OUTPUT_DIR = "tests/test_outputs"
    TIMEOUT = 30  # seconds
    RETRY_COUNT = 3
    EXPECTED_RESPONSE_TIME = 5  # seconds

@pytest.fixture
def pipe():
    """Fixture to create a Pipe instance for testing"""
    return Pipe(local_testing=True)

@pytest.fixture
def mock_user():
    """Fixture for mock user data"""
    return {
        "id": "123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "tester",
    }

@pytest.fixture
def mock_event_emitter():
    """Fixture for mock event emitter"""
    async def emitter(event):
        console.log(f"[dim]Event emitted: {event}[/dim]")
    return emitter

@pytest.fixture
def test_scenarios():
    """Fixture for test scenarios"""
    return {
        "scenario_conflict_classification": {
            "messages": [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "assistant", "content": "Hello! How can I help you?"},
                {"role": "user", "content": "I'm curious about the conflict in Lebanon."},
                {
                    "role": "assistant",
                    "content": "Sure! Are you interested in classification or specific details?",
                },
                {
                    "role": "user",
                    "content": "Specifically, I'd like to know if it's an International or Non-International Armed Conflict.",
                },
            ],
            "expected_content": ["conflict", "classification", "Lebanon"],
            "timeout": 30,
        },
        "scenario_rulac_query": {
            "messages": [
                {"role": "user", "content": "What conflicts are taking place in Syria?"},
            ],
            "expected_content": ["Syria", "conflict", "RULAC"],
            "timeout": 45,
        },
        # Add more scenarios here
    }

class TestPipe:
    """Test class for Pipe functionality"""

    @pytest.mark.asyncio
    async def test_pipe_scenarios(
        self, pipe, mock_user, mock_event_emitter, test_scenarios
    ):
        """Test multiple scenarios with improved reporting and error handling"""
        results: List[TestResult] = []
        
        # Create output directory if it doesn't exist
        os.makedirs(TestConfig.OUTPUT_DIR, exist_ok=True)

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Running test scenarios...", total=len(test_scenarios)
            )

            for scenario_name, scenario_data in test_scenarios.items():
                try:
                    # Start timing
                    start_time = time.time()

                    # Prepare test data
                    body = {"messages": scenario_data["messages"]}
                    expected_content = scenario_data.get("expected_content", [])
                    timeout = scenario_data.get("timeout", TestConfig.TIMEOUT)

                    # Run the test with timeout
                    async with asyncio.timeout(timeout):
                        response = await pipe.pipe(
                            body,
                            mock_user,
                            None,
                            mock_event_emitter,
                            local_testing=True
                        )

                    # Calculate duration
                    duration = time.time() - start_time

                    # Validate response
                    success = True
                    error = None
                    actual_content = []

                    # Check if response contains expected content
                    if expected_content:
                        response_text = response if isinstance(response, str) else str(response)
                        actual_content = [
                            content for content in expected_content
                            if content.lower() in response_text.lower()
                        ]
                        success = len(actual_content) == len(expected_content)

                    # Create test result
                    result = TestResult(
                        scenario_name=scenario_name,
                        success=success,
                        duration=duration,
                        response=response,
                        expected_content=expected_content,
                        actual_content=actual_content,
                    )

                    # Save response to file
                    if response:
                        output_file = os.path.join(
                            TestConfig.OUTPUT_DIR,
                            f"{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        )
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(str(response))

                    results.append(result)

                except asyncio.TimeoutError:
                    results.append(
                        TestResult(
                            scenario_name=scenario_name,
                            success=False,
                            duration=timeout,
                            error=f"Test timed out after {timeout} seconds",
                        )
                    )
                except Exception as e:
                    results.append(
                        TestResult(
                            scenario_name=scenario_name,
                            success=False,
                            duration=time.time() - start_time,
                            error=str(e),
                        )
                    )

                finally:
                    progress.update(task, advance=1)

        # Generate test report
        self._generate_test_report(results)

    def _generate_test_report(self, results: List[TestResult]):
        """Generate a detailed test report"""
        # Create summary table
        table = Table(title="Test Results Summary")
        table.add_column("Scenario", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Duration (s)", justify="right")
        table.add_column("Expected Content", style="yellow")
        table.add_column("Actual Content", style="yellow")

        for result in results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            status_style = "green" if result.success else "red"
            
            table.add_row(
                result.scenario_name,
                f"[{status_style}]{status}[/{status_style}]",
                f"{result.duration:.2f}",
                str(result.expected_content or []),
                str(result.actual_content or []),
            )

        console.print(table)

        # Print detailed results
        console.print("\n[bold]Detailed Test Results:[/bold]")
        for result in results:
            panel = Panel(
                f"""
                [bold]Scenario:[/bold] {result.scenario_name}
                [bold]Status:[/bold] {'✅ PASS' if result.success else '❌ FAIL'}
                [bold]Duration:[/bold] {result.duration:.2f} seconds
                [bold]Error:[/bold] {result.error or 'None'}
                """,
                title=f"Test Result: {result.scenario_name}",
                border_style="green" if result.success else "red",
            )
            console.print(panel)

        # Print performance summary
        avg_duration = sum(r.duration for r in results) / len(results)
        console.print(f"\n[bold]Average Test Duration:[/bold] {avg_duration:.2f} seconds")

    @pytest.mark.asyncio
    async def test_pipe_error_handling(self, pipe, mock_user, mock_event_emitter):
        """Test error handling scenarios"""
        error_scenarios = [
            {
                "name": "empty_messages",
                "body": {"messages": []},
                "expected_error": "No messages provided",
            },
            {
                "name": "invalid_message_format",
                "body": {"messages": [{"invalid": "format"}]},
                "expected_error": "Invalid message format",
            },
            # Add more error scenarios
        ]

        for scenario in error_scenarios:
            try:
                await pipe.pipe(
                    scenario["body"],
                    mock_user,
                    None,
                    mock_event_emitter,
                    local_testing=True
                )
                pytest.fail(f"Expected error for scenario: {scenario['name']}")
            except Exception as e:
                assert scenario["expected_error"] in str(e)

    @pytest.mark.asyncio
    async def test_pipe_performance(self, pipe, mock_user, mock_event_emitter):
        """Test performance with multiple concurrent requests"""
        async def run_request():
            body = {"messages": [{"role": "user", "content": "What conflicts are in Syria?"}]}
            start_time = time.time()
            await pipe.pipe(body, mock_user, None, mock_event_emitter, local_testing=True)
            return time.time() - start_time

        # Run multiple concurrent requests
        tasks = [run_request() for _ in range(3)]
        durations = await asyncio.gather(*tasks)

        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        console.print(f"""
        [bold]Performance Test Results:[/bold]
        Average Duration: {avg_duration:.2f} seconds
        Max Duration: {max_duration:.2f} seconds
        Min Duration: {min_duration:.2f} seconds
        """)

        # Assert performance requirements
        assert avg_duration < TestConfig.EXPECTED_RESPONSE_TIME, "Response time exceeds expected duration" 