from rich.console import Console
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Initialize Rich Console
console = Console()

# Function to extract graph schema using Neo4jGraph
def get_graph_schema(graph):
    """
    Extract schema from a Neo4j graph using Neo4jGraph.
    """
    console.log("[bold cyan]Extracting graph schema...[/bold cyan]")
    try:
        schema = graph.schema  # Access the schema property
        console.log(f"[bold yellow]Raw schema data:[/bold yellow]\n{schema}")
        
        # Parse the schema into nodes and relationships
        nodes = []
        relationships = []

        for line in schema.splitlines():
            line = line.strip()
            if line.startswith("- **") and "**" in line:
                # Extract node label
                node_label = line.split("**")[1].strip()
                nodes.append(node_label)
            elif line.startswith("(:"):
                # Extract relationship type
                rel_type = line.split("[:")[1].split("]")[0]
                relationships.append(rel_type)
        
        console.log("[bold green]Schema extracted successfully.[/bold green]")
        console.log(f"Nodes: {nodes}")
        console.log(f"Relationships: {relationships}")
        
        return {"nodes": nodes, "relationships": relationships}
    except Exception as e:
        console.log(f"[bold red]Error extracting graph schema: {e}[/bold red]")
        raise

# Function to generate question categories using ChatOpenAI
def generate_question_categories(llm, schema):
    """
    Generate question categories using a language model.
    """
    console.log("[bold cyan]Generating question categories...[/bold cyan]")
    
    schema_string = f"Nodes: {', '.join(schema['nodes'])}\nRelationships: {', '.join(schema['relationships'])}"
    
    prompt = f"""
    You are an expert in armed conflict and international humanitarian law (IHL). 
    I have a knowledge graph that focuses on topics such as conflicts, state and non-state actors, 
    applicable legal frameworks, and geographical regions involved in conflicts. 

    I want to generate 12 categories of questions researchers in this field might ask. 
    The questions should cover single-node details (e.g., specific conflicts or actors), 
    multi-node relationships (e.g., connections between conflicts and legal frameworks), 
    and paths (e.g., tracing conflict escalation through various actors and regions). 
    Focus on categories relevant to IHL, armed conflict classifications, and parties to conflicts.

    Here is the graph schema:
    {schema_string}
    """
    
    try:
        # Use the LangChain LLM interface
        messages = [
            SystemMessage(content="You are a helpful assistant specialized in IHL and armed conflict research."),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        categories = response.content
        console.log("[bold green]Categories generated successfully.[/bold green]")
        console.log(f"\n[bold yellow]Generated Categories:[/bold yellow]\n{categories}")
        return categories
    except Exception as e:
        console.log(f"[bold red]Error generating categories: {e}[/bold red]")
        return None

# Main function for testing
def main():
    """
    Main function to extract schema and generate question categories.
    """
    console.rule("[bold blue]Starting Test[/bold blue]")
    
    # Neo4j connection details
    neo4j_url = "bolt://localhost:7687"
    username = "neo4j"
    password = "password"
    
    console.log("[bold cyan]Connecting to Neo4j...[/bold cyan]")
    try:
        # Initialize the Neo4jGraph
        graph = Neo4jGraph(
            url=neo4j_url,
            username=username,
            password=password,
            enhanced_schema=True,
        )
        
        # Step 1: Extract schema
        schema = get_graph_schema(graph)
        
        # Step 2: Initialize ChatOpenAI LLM
        llm = ChatOpenAI(
            model="gpt-4o",  # Use "gpt-4o" or another compatible model
            temperature=0,
            max_tokens=None,
            max_retries=2,
        )
        
        # Step 3: Generate categories
        categories = generate_question_categories(llm, schema)
        
        # Output categories
        if categories:
            console.print(f"\n[bold magenta]Final Categories:[/bold magenta]\n{categories}")
        else:
            console.log("[bold red]Failed to generate categories.[/bold red]")
    except Exception as e:
        console.log(f"[bold red]Failed to connect to Neo4j or process schema: {e}[/bold red]")
        
    console.rule("[bold blue]Test Complete[/bold blue]")

# Run the test
if __name__ == "__main__":
    main()
