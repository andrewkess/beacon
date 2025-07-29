import json
import pandas as pd
from rich.console import Console
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_neo4j import Neo4jGraph
from pydantic import BaseModel, ValidationError
from typing import List

# Initialize Rich Console for logging
console = Console()

# Pydantic model for question validation
class QuestionItem(BaseModel):
    question: str

class QuestionsResponse(BaseModel):
    questions: List[QuestionItem]

# Function to extract graph schema using Neo4jGraph
def get_graph_schema(graph):
    console.log("[bold cyan]Extracting graph schema...[/bold cyan]")
    try:
        schema = graph.schema
        console.log(f"[bold yellow]Raw schema data:[/bold yellow]\n{schema}")

        nodes, relationships = [], []
        for line in schema.splitlines():
            line = line.strip()
            if line.startswith("- **") and "**" in line:
                nodes.append(line.split("**")[1].strip())
            elif line.startswith("(:"):
                relationships.append(line.split("[:")[1].split("]")[0])

        console.log("[bold green]Schema extracted successfully.[/bold green]")
        console.log(f"Nodes: {nodes}")
        console.log(f"Relationships: {relationships}")

        return {"nodes": nodes, "relationships": relationships}
    except Exception as e:
        console.log(f"[bold red]Error extracting graph schema: {e}[/bold red]")
        raise

# Function to clean and validate JSON response
def clean_and_validate_json(raw_response):
    """
    Cleans the raw JSON response by removing any non-JSON artifacts and validates it using Pydantic.
    """
    try:
        # Attempt to find the JSON content by ignoring markdown or extra artifacts
        start_idx = raw_response.find('{')
        end_idx = raw_response.rfind('}') + 1
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No valid JSON object found in the response.")
        
        cleaned_response = raw_response[start_idx:end_idx]

        # Validate with Pydantic
        validated_questions = QuestionsResponse.model_validate_json(cleaned_response)
        return validated_questions.questions
    except ValidationError as e:
        console.log(f"[bold red]Validation error: {e.json()}[/bold red]")
        return []
    except (ValueError, json.JSONDecodeError) as e:
        console.log(f"[bold red]JSON decoding error: {e}[/bold red]")
        return []


# Function to generate natural language questions with mock data for a specific category
def generate_questions_with_mock_data(llm, schema, category):
    console.log(f"[bold cyan]Generating questions with mock data for category: {category}[/bold cyan]")

    schema_string = f"Nodes: {', '.join(schema['nodes'])}\nRelationships: {', '.join(schema['relationships'])}"

    prompt = f"""
    You are an expert in international humanitarian law (IHL) and armed conflict research. 
    Using the following knowledge graph schema, generate 10 diverse and meaningful 
    natural language questions for the category: "{category}". 

    Include specific mock data in the questions, such as:
    - Conflict names (e.g., 'Libyan Civil War', 'Yemeni Civil War')
    - State actors (e.g., 'United States', 'Russia', 'Somalia')
    - Non-state actors (e.g., 'Boko Haram', 'Taliban')
    - Geographical regions (e.g., 'Northern Africa', 'Southern Asia', 'West Africa')

    Schema:
    {schema_string}

    Return the questions in the following JSON format:
    {{"questions": [{{"question": "Question 1"}}, {{"question": "Question 2"}}, ..., {{"question": "Question 10"}}]}}
    """

    try:
        messages = [
            SystemMessage(content="You are a helpful assistant specializing in IHL and question generation."),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        return clean_and_validate_json(response.content)
    except Exception as e:
        console.log(f"[bold red]Error generating questions for {category}: {e}[/bold red]")
        return []


# Save questions to a local JSON file
def save_questions_to_file(data, file_path):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        console.log(f"[bold green]Questions saved to {file_path} successfully.[/bold green]")
    except Exception as e:
        console.log(f"[bold red]Error saving questions to file: {e}[/bold red]")

# Main function for generating and saving questions
def main():
    console.rule("[bold blue]Starting Question Generation with Mock Data Test[/bold blue]")

    neo4j_url = "bolt://localhost:7687"
    username = "neo4j"
    password = "password"
    file_path = "questions_with_mock_data.json"

    console.log("[bold cyan]Connecting to Neo4j...[/bold cyan]")
    try:
        graph = Neo4jGraph(
            url=neo4j_url,
            username=username,
            password=password,
            enhanced_schema=True,
        )

        schema = get_graph_schema(graph)

        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_tokens=2000,
            max_retries=2,
        )

        categories = [
            "Specific Conflict Details",
            # "State and Non-State Actors",
            # "Legal Frameworks and Classifications",
        ]

        all_questions = []

        for category in categories:
            questions = generate_questions_with_mock_data(llm, schema, category)
            for item in questions:
                all_questions.append({"Category": category, "Question": item.question})

        save_questions_to_file(all_questions, file_path)

        df = pd.DataFrame(all_questions)
        console.print("\n[bold magenta]Generated Questions Dataset:[/bold magenta]")
        console.print(df)

    except Exception as e:
        console.log(f"[bold red]Failed to connect to Neo4j or process schema: {e}[/bold red]")

    console.rule("[bold blue]Test Complete[/bold blue]")

# Run the test
if __name__ == "__main__":
    main()
