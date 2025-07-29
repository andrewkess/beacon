# Beacon

Beacon is an advanced LLM pipeline that integrates with OpenWebUI to provide research-enhanced conversations about armed conflicts, international humanitarian law, and human rights.

## Overview

Beacon uses a sophisticated routing system to determine whether user queries require research tools or can be answered using general knowledge. When research is needed, Beacon employs specialized tools to retrieve relevant information from authoritative sources like RULAC (Rule of Law in Armed Conflicts) and web searches, providing citations to support its responses.

## Architecture

The system comprises two main components:

1. **DRAGON_Beacon_v1.py** - The core pipeline that handles user messages, routes them to appropriate LLMs, manages tool usage, and generates responses
2. **retrieveRULAC_tools.py** - A collection of specialized tools for querying conflict data from various sources

## Key Process Flow

1. **User Query Intake**
   - The system receives conversational messages from OpenWebUI
   - Messages are passed to the `pipe()` function which orchestrates the entire process

2. **Intent Classification (Router)**
   - The Router LLM analyzes the full conversation context
   - Determines if the query requires research tools or can be answered with general knowledge
   - Classifies as either `USE_RESEARCH_TOOL_LLM` or `USE_GENERAL_LLM`

3. **Query Processing**
   - **General Queries**: Handled by the general model with streaming responses
   - **Research Queries**: Processed through the following steps:
     - Tool selection and execution
     - Information retrieval from sources like RULAC or web search
     - Citation collection and management
     - Final answer generation using retrieved information

4. **Citation Management**
   - Citations from research tools are collected and deduplicated
   - Unique citations are emitted as events for display in the UI
   - Citation counts are tracked and reported to users

5. **Response Generation**
   - Responses are streamed back to OpenWebUI
   - For research queries, responses incorporate findings from tools
   - For general queries, the system provides direct answers

## Tools

Beacon includes specialized tools for:

- Retrieving conflict data by state actor involvement
- Retrieving conflict data by non-state actor involvement
- Retrieving conflict data by country/region
- Retrieving conflict data by organization
- Fetching general RULAC information
- Retrieving conflict classification methodology
- Retrieving information about international humanitarian law frameworks
- Web search capabilities
- Website content retrieval

## Neo4j Graph Database Integration

Beacon leverages a Neo4j graph database as the backend for its RULAC tools, providing significant advantages for armed conflict research:

1. **Relationship-Centric Data Model**
   - Armed conflicts naturally involve complex relationships between actors (states, non-state groups, organizations)
   - Neo4j's graph structure efficiently maps these relationships, making it ideal for conflict data

2. **Powerful Query Capabilities**
   - Cypher query language enables precise, relationship-based searches
   - RULAC tools dynamically generate Cypher queries based on user questions
   - Allows for traversing complex relationships (e.g., "conflicts involving both X and Y actors")

3. **Performance Advantages**
   - Fast retrieval of connected data compared to traditional relational databases
   - Efficient for queries that would require multiple joins in SQL databases

4. **Flexibility for Complex Data**
   - Schema flexibility accommodates the varied nature of conflict data
   - Properties can be easily added to nodes and relationships as new information emerges

5. **Visualization Potential**
   - Graph data model supports natural visualization of conflict networks
   - Helps identify patterns and connections between different conflicts

The RULAC tools initialize a connection to Neo4j, execute tailored Cypher queries, and process the results to provide comprehensive conflict data with proper citation tracking.

## LLM Models

The system uses different LLM models for specific purposes:

1. **Router Model**: A quick and efficient model for intent classification
2. **General Model**: A larger model for handling general queries
3. **Tool Model**: A versatile model with tool-use capabilities for research tasks

## Events System

Beacon employs an event system for:
- Status updates to the UI during processing
- Citation emission for reference tracking
- Progress indicators during multi-stage operations

## Testing Suite

The codebase includes comprehensive testing functionality:
- Scenario-based testing for different query types
- Router testing for intent classification verification
- Tool execution testing for verifying research capabilities
- End-to-end pipeline testing

## Requirements

The system requires several dependencies including:
- LangChain components
- Various LLM provider SDKs (Groq, Mistral, etc.)
- FastAPI for integration
- Other utility packages for processing and logging

## Integration

Beacon is designed to work with OpenWebUI, accepting conversation messages and returning streaming responses that can be displayed in the UI.
