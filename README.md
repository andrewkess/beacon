# Beacon: A Conversational AI for Conflict Classification and International Humanitarian Law Research

Beacon is a conversational AI application that dynamically routes and answers questions on armed conflicts and IHL using a Neo4j-backed RULAC database, while gracefully handling general queries.

## Overview

This repository contains a conversational AI application integrating large language models (LLMs) with a custom “router” mechanism and specialized research tools. It can:

- **Classify Conflict & International Humanitarian Law (IHL) Queries**  
  Detect and route questions related to armed conflict classification (IAC, NIAC, military occupation) and human rights violations to a specialized research chain.

- **Query a Neo4j-Backed RULAC Database**  
  Dynamically generate Cypher queries to retrieve relevant conflict data—parties involved, legal definitions, and geographical details—from the Rule of Law in Armed Conflict (RULAC) portal, stored in a Neo4j graph.

- **Provide Structured JSON Responses**  
  Return answers in a well-defined schema, ensuring each response includes sources, reasoning, conflicts identified, and a final synthesis.

- **Flexible General Queries**  
  If a user’s question is **not** IHL or human-rights–related, the system gracefully handles it through a fallback model, offering general assistance without specialized conflict research.

By combining **LangChain**-style tool invocation, a sophisticated **router LLM** for message classification, and **event-driven** updates (with citations and status logs), OpenWebUI delivers a structured, citation-backed conversation experience for IHL and human-rights research.
