# Beacon Project Documentation

This document provides detailed technical information about the tools used in the Beacon system, how they function, and recommendations for improvement.

## System Architecture Overview

Beacon is built as a tool-augmented LLM system that enhances responses through specialized research capabilities. The system follows a structured pipeline:

1. **Router Agent** - Analyzes incoming queries and determines whether to use specialized research tools or provide general information
2. **Research Agent** - Uses domain-specific tools to gather information from databases and the web
3. **General Agent** - Handles general queries without requiring specialized research tools

### Pipeline Processing Flow

1. The Router determines query type and redirects accordingly
2. For research queries, the Research Agent selects appropriate tools and invokes them
3. Tool outputs are collected and passed to a final response generator 
4. Citations are tracked and exposed to the user interface

## Tool System Overview

Beacon uses a tool-augmented LLM approach to enhance responses with specialized research capabilities. Tools are exposed to the LLM through function descriptions that enable the model to:

1. Understand when to invoke each tool
2. Provide proper parameters to the tool
3. Process and integrate the tool's output into the final response

### Standardized Tool Result Format

The system has evolved to use standardized tool output formats:

```python
class Citation(TypedDict):
    """TypedDict for standardized citation format used throughout tools."""
    title: str
    url: str
    formatted_content: str

class RULAC_TOOL_RESULT(TypedDict):
    """TypedDict for standardized tool result format."""
    content: Union[str, List[Dict[str, Any]], Dict[str, Any]]
    citations: List[Citation]
    tool_use_metadata: Optional[Dict[str, Any]]
```

This standardization allows for consistent citation tracking and UI integration.

### How Tool Descriptions Guide LLM Usage

The tool LLM relies on tool descriptions to understand their functionality and proper usage. These descriptions serve as a form of "API documentation" for the AI. Each tool description includes:

- **Function name**: Identifies the tool uniquely
- **Description**: Explains what the tool does and when to use it
- **Parameters**: Defines the inputs required by the tool
- **Return type**: Specifies the output format

Example from the code:
```python
@tool
async def retreive_RULAC_conflict_data_by_state_actor_involvement(
    research_query: str,
    target_state_actor_UN_M49_codes: List,
    target_conflict_types: List,
) -> RULAC_TOOL_RESULT:
    """
    Retreives RULAC conflict data about conflicts involving specific state actors.
    
    Args:
        research_query: The research question being asked
        target_state_actor_UN_M49_codes: List of UN M49 country codes to search for state actor involvement
        target_conflict_types: List of conflict types to filter by (IAC, NIAC, etc.)
        
    Returns:
        A RULAC_TOOL_RESULT containing the research content and citations
    """
```

When the LLM is instructed to use tools, it:
1. Analyzes the user query to determine which tools are relevant
2. Extracts or infers the necessary parameters from the user's question
3. Invokes the tool with those parameters
4. Processes the returned information to formulate a response

## Router Implementation

The system uses a dedicated Router class to determine how to process incoming queries:

```python
# Initialize the router class with our model
self.router = Router(self.router_model)
```

The Router examines conversation messages and classifies the request into one of two categories:
- `RESEARCH_AGENT` - For queries requiring specialized knowledge or research
- `BEACON_BASE_AGENT` - For general information or non-research queries

The Router also extracts key context from the conversation and provides a research subject for UI display.

## Detailed Tool Documentation

### RULAC Research Tools

#### 1. retreive_RULAC_conflict_data_by_state_actor_involvement

**Purpose**: Retrieves data about conflicts where specific state actors are involved as parties.

**Parameters**:
- `research_query`: The original research question from the user
- `target_state_actor_UN_M49_codes`: List of UN M49 country codes to identify state actors
- `target_conflict_types`: List of conflict types (IAC, NIAC, Military Occupation)

**Functionality**: 
This tool connects to the Neo4j database, constructs a Cypher query to find conflicts where the specified states are active participants, and returns detailed information about those conflicts including other parties involved, applicable international humanitarian law, and conflict classification.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What conflicts is France involved in?" or "List all International Armed Conflicts involving Russia."

#### 2. retreive_RULAC_conflict_data_by_non_state_actor_involvement

**Purpose**: Retrieves data about conflicts where specific non-state actors are involved.

**Parameters**:
- `research_query`: The original research question from the user
- `target_non_state_actor_name_and_aliases`: List of non-state actor names to search for

**Functionality**: 
Queries the Neo4j database for conflicts involving specific non-state armed groups or organizations, accounting for possible name variations and aliases.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What conflicts involve Boko Haram?" or "Which conflicts include the Wagner Group?"

#### 3. retreive_RULAC_conflict_data_by_conflict_taking_place_in_country

**Purpose**: Retrieves data about conflicts occurring within specific countries.

**Parameters**:
- `research_query`: The original research question from the user
- `target_country_UN_M49_codes`: List of UN M49 country codes where conflicts are occurring
- `target_conflict_types`: List of conflict types to filter by

**Functionality**: 
Searches for conflicts based on geographic location rather than participation, finding conflicts that take place within the specified countries.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What conflicts are happening in Ukraine?" or "List all conflicts taking place in Syria."

#### 4. retreive_RULAC_conflict_data_by_organization

**Purpose**: Retrieves data about conflicts involving specific international organizations.

**Parameters**:
- `research_query`: The original research question from the user
- `target_organization_name`: List of organization names to search for
- `target_conflict_types`: List of conflict types to filter by

**Functionality**: 
Queries for conflicts involving international organizations like NATO, the UN, African Union, etc.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What conflicts involve NATO?" or "Which conflicts have UN peacekeeping operations?"

#### 5. retreive_RULAC_conflict_data_by_region

**Purpose**: Retrieves data about conflicts taking place in specific geographical regions.

**Parameters**:
- `research_query`: The original research question from the user
- `target_region_UN_M49_codes`: List of UN M49 region codes to search within
- `target_conflict_types`: List of conflict types to filter by

**Functionality**: 
Searches for conflicts based on broader regional designations rather than specific countries.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What conflicts are occurring in Eastern Europe?" or "List all conflicts in North Africa."

#### 6. getBaselineRULACinformation

**Purpose**: Provides general background information about RULAC.

**Parameters**:
- `research_query`: The original research question from the user

**Functionality**: 
Returns basic information about the Rule of Law in Armed Conflicts (RULAC) project, its methodology, and objectives.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What is RULAC?" or "Tell me about the RULAC database."

#### 7. get_Conflict_Classification_Methodology

**Purpose**: Explains how RULAC classifies different types of armed conflicts.

**Parameters**:
- `research_query`: The original research question from the user

**Functionality**: 
Provides detailed information about RULAC's methodology for classifying conflicts as International Armed Conflicts (IAC), Non-International Armed Conflicts (NIAC), or Military Occupations.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "How does RULAC classify armed conflicts?" or "What's the difference between IAC and NIAC?"

#### 8. get_International_Humanitarian_Legal_Framework

**Purpose**: Provides information about relevant international humanitarian law.

**Parameters**:
- `research_query`: The original research question from the user

**Functionality**: 
Returns information about the legal frameworks governing armed conflicts, including the Geneva Conventions, Additional Protocols, and customary international law.

**Returns**: A `RULAC_TOOL_RESULT` containing content and standardized citations.

**Example Use Case**: "What laws apply during armed conflict?" or "Explain the legal framework of international humanitarian law."

### Web Search Tools

#### 9. brave_search

**Purpose**: Performs web searches for current information.

**Parameters**:
- `query`: The search query

**Functionality**: 
Searches the web using SearXNG search engine to retrieve current information that might not be in the RULAC database. The tool scrapes multiple results, processes them, and returns structured content with citations.

**Returns**: A standardized result with content and citations for each retrieved result.

**Example Use Case**: "What's the latest on the conflict in Gaza?" or "Recent developments in Ukraine war."

#### 10. get_website

**Purpose**: Retrieves and processes content from specific websites.

**Parameters**:
- `url`: The URL to scrape
- `doc_type`: Type of document (html, pdf)

**Functionality**: 
Fetches content from a specific URL, processes it, and extracts relevant text for analysis. Supports both HTML and PDF content with appropriate processing for each.

**Returns**: A standardized result with the processed content and citation information.

**Example Use Case**: When a user shares a specific URL for analysis or when the LLM needs to check a primary source.

## Citation Handling

The system implements comprehensive citation tracking through:

1. **Standardized Citation Format**: All tools use a consistent Citation format with title, URL, and formatted content
2. **Global Citation Tracking**: Citations are tracked globally across a session to avoid duplicates
3. **UI Integration**: Citations are emitted to the UI for user reference using a standardized event format
4. **Source Attribution**: Citations distinguish between RULAC data sources and web sources

Example of citation event emission:
```python
citation_event = {
    "type": "citation",
    "data": {
        "document": [formatted_content],
        "metadata": [
            {
                "date_accessed": datetime.now().isoformat(),
                "source": citation_title,
            }
        ],
        "source": {
            "name": citation_url, 
            "url": citation_url
        },
    }
}
await self.emit_event(citation_event)
```

## LLM Models and Prompting

The system uses multiple specialized LLMs for different purposes:

1. **Router Model**: Fast LLM for query classification
   ```python
   self.router_model = ChatGroq(groq_api_key=self.valves.groq_api_key, model="llama-3.1-8b-instant", temperature=0)
   ```

2. **General Model**: More capable model for general queries
   ```python
   self.general_model = ChatGroq(groq_api_key=self.valves.groq_api_key, model="llama3-70b-8192", temperature=0, streaming=True)
   ```

3. **Tool Model**: Model capable of tool use for research tasks
   ```python
   self.tool_model = ChatGroq(groq_api_key=self.valves.groq_api_key, model="llama-3.3-70b-versatile", temperature=0)
   ```

4. **Final Response Model**: Model for synthesizing research results (using Mistral)
   ```python
   chat_client = ChatMistralAI(
       api_key=self.valves.mistral_api_key,
       model="mistral-large-latest",
       temperature=0.2,
       max_retries=2,
       streaming=True
   )
   ```

Each model uses specialized prompts to guide its behavior and task execution.

## Recommendations for Tool Improvement

### Naming Standardization

The current tool naming conventions could benefit from standardization:

1. **Correct spelling**: Fix "retreive" to "retrieve" across all function names for consistency.
   
2. **Consistent naming pattern**: Standardize the naming convention, for example:
   - `rulac_conflict_by_state_actor`
   - `rulac_conflict_by_non_state_actor`
   - `rulac_conflict_by_country`
   - `rulac_conflict_by_organization`
   - `rulac_conflict_by_region`
   - `rulac_baseline_info`
   - `rulac_classification_methodology`
   - `rulac_legal_framework`

3. **Simplify parameter names**: Shorten lengthy parameter names while maintaining clarity:
   - `target_state_actor_UN_M49_codes` → `state_codes`
   - `target_non_state_actor_name_and_aliases` → `non_state_actors`
   - `target_country_UN_M49_codes` → `country_codes`

### Structural Improvements

1. **Parameter standardization**: Adopt a more consistent parameter structure across all tools:
   - Make all tools accept a similar set of parameters where possible
   - Use consistent parameter ordering across similar tools

2. **Return type standardization**: The code has already made significant progress with standardized `RULAC_TOOL_RESULT` and `Citation` types, which should be further leveraged across all tools.

3. **Tool description enhancement**: Add more context and examples in the docstrings to help the LLM understand when to use each tool.

4. **Parameter validation**: Add consistent parameter validation across all tools to prevent errors.

5. **Tool categorization**: Consider organizing tools in namespaces or modules based on functionality:
   - `rulac.by_state`
   - `rulac.by_country`
   - `web.search`
   - `web.get_content`

### Integration Improvements

1. **Combine related functionality**: Consider merging very similar tools with optional parameters to reduce the total number of tools.

2. **Progressive detail**: Structure tools to allow for progressive detail gathering, starting with general information and allowing follow-up specific queries.

3. **Results pagination**: Add pagination support for tools that might return large amounts of data.

4. **Error handling**: Implement more robust error handling in web tools to handle timeouts, invalid URLs, and rate limiting.

5. **Caching mechanism**: Add caching for frequently accessed data or recent searches to improve response times.

6. **Router refinement**: Enhance the router with more specialized categories to better direct queries to appropriate tools or specialized agents.

By implementing these recommendations, the Beacon system could become more maintainable, easier for the LLM to use effectively, and more resilient to different types of queries. 