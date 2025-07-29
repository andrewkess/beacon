## fine_tuning/2_generate_cypher_synthetic_data.py

import json
import asyncio
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain.prompts import PromptTemplate
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import pandas as pd
import logging
import os
from langchain_mistralai import ChatMistralAI
import coloredlogs
from langchain_groq import ChatGroq
from colorama import Fore, Style
from datetime import datetime
# from mistralai import Mistral
# from fine_tuning.chatMistralAgentLLM import ChatMistralAgent



# Setup logging and console
console = Console(log_path=False, width=100)
event_console = Console(log_path=False, width=100)

if "MISTRAL_API_KEY" not in os.environ:
    os.environ["MISTRAL_API_KEY"] = "9hblEwepQtzvyY9y4incc3yvApk4ArJO"

# Configure logging
logger = logging.getLogger("Beacon")
coloredlogs.install(
    logger=logger,
    level="INFO",  # Default logging level set to DEBUG
    isatty=True,
    fmt="%(asctime)s [%(levelname)s] %(message)s",
)



# Load existing results and track previously processed questions
def load_existing_results(output_file):
    try:
        with open(output_file, "r") as f:
            existing_results = json.load(f)
            processed_questions = {entry["Input"].strip().lower() for entry in existing_results}
            
            # Debugging
            console.log(f"[bold cyan]Loaded {len(existing_results)} existing results.[/bold cyan]")
            console.log(f"[bold cyan]Sample of processed questions:[/bold cyan] {list(processed_questions)[:5]}")

            return existing_results, processed_questions
    except (FileNotFoundError, json.JSONDecodeError):
        return [], set()

def load_questions(file_path):
    """
    Load questions from a JSON file where each question is a dictionary with keys:
    - "category"
    - "question"
    - "country" (optional)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        questions = json.load(file)
    
    console.log(f"[bold cyan]Loaded {len(questions)} questions from {file_path}.[/bold cyan]")
    return questions



# Ensure only new questions are processed
def get_new_questions(questions, processed_questions):
    new_questions = []
    for q in questions:
        question_text = q["question"].strip().lower()
        if question_text not in processed_questions:
            new_questions.append(q)
        else:
            console.log(f"[bold yellow]Skipping already processed question:[/bold yellow] {q['question']}")

    # Debugging: Show exactly what is happening
    console.log(f"[bold cyan]Total questions in baseline file: {len(questions)}[/bold cyan]")
    console.log(f"[bold cyan]Total processed questions from output file: {len(processed_questions)}[/bold cyan]")
    console.log(f"[bold cyan]New questions to process: {len(new_questions)}[/bold cyan]")

    return new_questions

# Save results to JSON file
def save_results(output_file, results):
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    console.log(f"[bold green]Results saved to {output_file} successfully.[/bold green]")




# Mock PipeSelf class
class PipeSelf:
    neo4j_url = "bolt://localhost:7687"
    valves = {"neo4j_username": "neo4j", "neo4j_password": "password"}

# Mock event emitter
async def mock_event_emitter(event):
    if event["type"] == "citation":
        document_content = event["data"]["document"][0]
        event_console.print(
            Panel(
                Markdown(document_content), 
                title=f"Citation: {event['data']['source']['name']}", 
                style="black on yellow"
            )
        )
        # event_console.print(
        #     Panel(
        #         Markdown(document_content), 
        #         title=f"Citation: {event['data']['source']['name']}", 
        #         style="black on yellow"
        #     )
        # )

# Extract generated Cypher query
def extract_generated_query(result):
    intermediate_steps = result.get("intermediate_steps", [])
    for step in intermediate_steps:
        if "query" in step:
            return step["query"]
    return "No generated query found"

# Validate processed result before saving (remove "Output" key)
def is_valid_result(result):
    required_keys = {"Category", "Input", "Generated Query"}
    # Ensure all required keys are present and non-empty
    if not all(key in result and result[key] for key in required_keys):
        return False
    return "Citations Emitted" in result


# Process a single question
async def process_question(question_data, pipe_self, event_emitter):
    global citations_emitted_per_question
    category = question_data["category"]
    question = question_data["question"]

    console.log(f"[bold magenta]Processing question from category: {category}[/bold magenta]")
    citations_emitted_per_question = 0

    try:
        result = await get_conflict_classification_and_IHL_law_research(
            query=question, pipeSelf=pipe_self, event_emitter=event_emitter
        )
        generated_query = extract_generated_query(result)
        
        # Display the generated query
        console.print(
            Panel(
                Markdown(f"Generated Cypher Query Successful"),
                title=f"[bold cyan]{question}\n - {citations_emitted_per_question} citations[/bold cyan]",
                border_style="blue",
            )
        )

        # Wrap query in backticks for formatting in the saved results
        formatted_query = f"```\n{generated_query}\n```"

        return {
            "Category": category,
            "Input": question,
            "Generated Query": formatted_query,
            "Citations Emitted": citations_emitted_per_question,
        }
    except Exception as e:
        console.log(f"[bold red]Error processing query: {e}[/bold red]")
        return {
            "Category": category,
            "Input": question,
            "Generated Query": None,
            "Citations Emitted": citations_emitted_per_question,
        }


# Process all questions
async def process_pipeline(questions, pipe_self, event_emitter):
    results = []
    for question_data in questions:
        result = await process_question(question_data, pipe_self, event_emitter)
        results.append(result)
    return results

# Ensure unique citations are emitted



async def _emit_citations(result, __event_emitter__, model_label):
    global citations_emitted_per_question
    intermediate_steps = result.get("intermediate_steps", [])
    emitted_citations = set()

    # print(f"{Fore.GREEN}{Style.BRIGHT}INTERMEDIATE STEPS{Style.RESET_ALL}")
    # print(intermediate_steps)



    for step in intermediate_steps:
        # Extract context generated by the model
        context_list = step.get("context", [])
        if not isinstance(context_list, list):
            context_list = [context_list]

        for context_item in context_list:
            research_data = context_item.get("RULAC_research", {})
            summary = research_data.get("summary", [])

            conflict_details = research_data.get("conflict_details", [])

            for conflict in conflict_details:
                citation_url = conflict.get("conflict_citation")
                if not citation_url or citation_url in emitted_citations:
                    continue

                emitted_citations.add(citation_url)
                citations_emitted_per_question += 1

                # Convert state and non-state parties to comma-separated strings
                state_parties = conflict.get("state_parties", "N/A")
                non_state_parties = conflict.get("non_state_parties", "N/A")


                document_content = f"**Conflict Profile:** {conflict.get('conflict_name', 'N/A')}\n\n"
                document_content += f"**Classification:** {conflict.get('conflict_classification', 'N/A')}\n\n"
                document_content += f"**Overview:** {conflict.get('conflict_overview', 'N/A')}\n\n"
                document_content += f"**Applicable IHL:** {conflict.get('applicable_ihl_law', 'N/A')}\n\n"
                # Only include Non-State Actors if not empty
                if state_parties.strip():
                    document_content += f"**State Actors Party to Conflict:** {state_parties}\n\n"
                # Only include Non-State Actors if not an empty list or empty string
                if non_state_parties.strip():
                    document_content += f"**Non-State Actors Party to Conflict:** {non_state_parties}\n"


                await __event_emitter__(
                    {
                        "type": "citation",
                        "data": {
                            "document": [document_content],
                            "metadata": [{"source": citation_url}],
                            "source": {"name": conflict.get("conflict_name", "Unknown Conflict")},
                        },
                    }
                )

    if intermediate_steps:

        generated_cypher_query = intermediate_steps[0].get("query", "")
        logger.info(f"{Fore.BLUE}{Style.BRIGHT}Generated Cypher Query:\n\n{generated_cypher_query}{Style.RESET_ALL}")

        logger.info(f"{Fore.YELLOW}{Style.BRIGHT}Intelligent Cypher Summary:\n\n{summary}{Style.RESET_ALL}")

     
async def main():
    console.rule("[bold blue]Starting Conflict Classification and IHL Law Research[/bold blue]")

    # File paths
    questions_file = "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/output_questions.json"
    output_file = "pipeline_results_MASTER_V3.json"

    # Load questions and existing results
    questions = load_questions(questions_file)
    existing_results, processed_questions = load_existing_results(output_file)
    console.log(f"[bold cyan]Loaded {len(questions)} questions from baseline file.[/bold cyan]")
    
    new_questions = get_new_questions(questions, processed_questions)
    if not new_questions:
        console.log("[bold yellow]No new questions to process.[/bold yellow]")
        return

    # Set the maximum number of concurrent tasks (batch size)
    batch_size = 1
    semaphore = asyncio.Semaphore(batch_size)
    pipe_self = PipeSelf()
    valid_results = []

    async def process_and_save(q):
        async with semaphore:
            result = await process_question(q, pipe_self, mock_event_emitter)
            if is_valid_result(result):
                # Immediately load, append, and save the result.
                existing_results, _ = load_existing_results(output_file)
                existing_results.append(result)
                save_results(output_file, existing_results)
                valid_results.append(result)
            else:
                console.log(f"[bold red]Skipping invalid result for question: {result['Input']}[/bold red]")
            return result

    # Schedule all tasks but limit concurrency via the semaphore
    tasks = [asyncio.create_task(process_and_save(q)) for q in new_questions]

    # Process tasks as soon as they complete
    for finished_task in asyncio.as_completed(tasks):
        await finished_task  # Each task's result is saved as soon as it is done

    # Display final results
    if valid_results:
        df = pd.DataFrame(valid_results)
        console.print("\n[bold magenta]Generated Research Results:[/bold magenta]")
        console.print(df)
    else:
        console.log("[bold red]No valid results generated.[/bold red]")
    console.rule("[bold blue]Test Complete[/bold blue]")


def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Retrieve data by only running the Cypher generation chain
async def get_conflict_classification_and_IHL_law_research(query, pipeSelf=None, event_emitter=None):
    console.rule("[bold cyan]NEO4J Cypher Generation Tool: Start[/bold cyan]")
    console.log(f"[bold yellow]Received TOOL query from tool model:[/bold yellow] {query}")

    # Connect to Neo4j
    graph = Neo4jGraph(
        url="bolt://localhost:7687",
        username="neo4j",
        password="password",
        enhanced_schema=False,
    )
    console.log("[bold green]Successfully connected to Neo4j.[/bold green]")

    # Use ChatMistralAI to generate a Cypher query
    cypher_llm = ChatMistralAI(model="codestral-latest", temperature=0, max_retries=2)

    # Create the chain; note that we do not need a QA prompt here
    chain = GraphCypherQAChain.from_llm(
        llm=cypher_llm,
        graph=graph,
        cypher_prompt=PromptTemplate(
            input_variables=["schema", "question"],
            template=load_template_from_file(
                "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/prompts/coestral_RULAC_neo_systemOPT_SYNTH.md"
            ),
        ),
        return_intermediate_steps=True,
        allow_dangerous_requests=True,
        verbose=True,
    )
    # console.print("[bold green]NEO4J SCHEMA[/bold green]")
    # console.print(graph.schema)

    # Use the cypher_generation_chain directly to generate the query
    args = {"schema": graph.schema, "question": query}
    raw_cypher = chain.cypher_generation_chain.invoke(args)
    # Optionally, if the generated text is wrapped in backticks, you can extract the query:
    generated_cypher = raw_cypher  # or: generated_cypher = extract_cypher(raw_cypher)

    logger.info(f"{Fore.BLUE}{Style.BRIGHT}Generated Cypher Query:\n\n{generated_cypher}{Style.RESET_ALL}")

    # Now query the graph using the generated cypher query
    context_data = graph.query(generated_cypher)

    # Prepare a result dictionary similar to your original structure
    result = {
        "result": context_data,
        "intermediate_steps": [{"query": generated_cypher, "context": context_data}],
    }

    # Optionally, emit citations if your citations logic still applies
    await _emit_citations(result, event_emitter, "ChatMistralAI")
    console.rule("[bold green]NEO4J Cypher Generation Tool: End[/bold green]")
    return result



# Helper to load templates
def load_template_from_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

# Run the script
if __name__ == "__main__":
    asyncio.run(main())
