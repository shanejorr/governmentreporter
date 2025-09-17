# MCP Server Implementation Structure

## Overview
The MCP (Model Context Protocol) server has been implemented to provide semantic search capabilities for US government documents to Large Language Models. The server retrieves relevant document chunks from Qdrant vector database and returns them formatted for LLM context windows.

## Directory Structure

```
src/governmentreporter/
├── server/                         # NEW MCP Server Module
│   ├── __init__.py                # Module exports and initialization
│   ├── mcp_server.py              # Main MCP server implementation
│   ├── handlers.py                # Tool handlers for MCP requests
│   ├── query_processor.py         # Result formatting for LLMs
│   └── config.py                  # Server configuration settings
├── server.py                      # NEW Main entry point for running the server
├── apis/                          # Existing - Government API clients
├── database/                      # Existing - Qdrant integration
├── processors/                    # Existing - Document processing
└── utils/                         # Existing - Shared utilities
```

## New Files Created

### 1. `src/governmentreporter/server/mcp_server.py`

**Purpose**: Main MCP server implementation that manages the server lifecycle and tool registration.

**Classes**:
- `GovernmentReporterMCP`: Main server class
  - **Methods**:
    - `__init__(config)`: Initialize server with configuration
    - `_register_handlers()`: Register MCP tool handlers
    - `initialize()`: Set up Qdrant connection and verify database
    - `start()`: Run the MCP server event loop
    - `shutdown()`: Gracefully close connections

**Functions**:
- `create_and_run_server()`: Convenience function to create and run server

**Key Features**:
- Manages MCP server lifecycle
- Registers 5 MCP tools for LLM interaction
- Handles async operations and graceful shutdown
- Provides connection management for Qdrant

---

### 2. `src/governmentreporter/server/handlers.py`

**Purpose**: Contains handler functions for each MCP tool exposed to LLMs.

**Functions**:
- `handle_search_government_documents(qdrant_client, arguments)`:
  - **Purpose**: Main semantic search across all collections
  - **Returns**: Formatted search results with document chunks
  - **Parameters**: query, document_types, limit

- `handle_search_scotus_opinions(qdrant_client, arguments)`:
  - **Purpose**: Specialized SCOTUS search with legal filters
  - **Returns**: SCOTUS-specific formatted results
  - **Parameters**: query, opinion_type, justice, date range, limit

- `handle_search_executive_orders(qdrant_client, arguments)`:
  - **Purpose**: Specialized EO search with policy filters
  - **Returns**: EO-specific formatted results
  - **Parameters**: query, president, agencies, policy_topics, date range, limit

- `handle_get_document_by_id(qdrant_client, arguments)`:
  - **Purpose**: Retrieve specific document/chunk by ID
  - **Returns**: Document content with metadata
  - **Parameters**: document_id, collection, full_document

- `handle_list_collections(qdrant_client, arguments)`:
  - **Purpose**: List available collections with statistics
  - **Returns**: Collection information and capabilities
  - **Parameters**: None

**Key Features**:
- Generates query embeddings using existing `embeddings.py`
- Builds Qdrant filter conditions for metadata filtering
- Handles errors gracefully with informative messages
- Supports optional full document retrieval from APIs

---

### 3. `src/governmentreporter/server/query_processor.py`

**Purpose**: Formats search results from Qdrant for optimal LLM consumption.

**Classes**:
- `QueryProcessor`: Main formatting class
  - **Methods**:
    - `format_search_results(query, results)`: Format general search results
    - `format_scotus_results(query, results)`: Format SCOTUS-specific results
    - `format_eo_results(query, results)`: Format Executive Order results
    - `format_document_chunk(collection, document_id, payload)`: Format single chunk
    - `format_full_document(doc_type, full_document, chunk_metadata)`: Format complete document
    - `format_collections_list(collections)`: Format collection information
    - `_format_scotus_chunk(index, payload, score, detailed)`: Internal SCOTUS formatter
    - `_format_eo_chunk(index, payload, score, detailed)`: Internal EO formatter
    - `_format_generic_chunk(index, payload, score)`: Fallback formatter
    - `_extract_relevant_metadata(collection, payload)`: Extract key metadata

**Key Features**:
- Preserves document structure in formatted output
- Truncates long chunks to prevent context overflow
- Emphasizes relevant metadata for each document type
- Provides consistent, readable formatting for LLMs
- Includes relevance scores and citations

---

### 4. `src/governmentreporter/server/config.py`

**Purpose**: Configuration management for the MCP server with environment variable support.

**Classes**:
- `ServerConfig`: Dataclass holding all server configuration
  - **Attributes**:
    - Server identification (name, version)
    - Collection mappings (document types to Qdrant collections)
    - Search parameters (limits, defaults)
    - Qdrant connection settings (host, port, API key)
    - Embedding configuration (model, dimensions)
    - Chunking configurations (SCOTUS and EO specific)
    - Caching settings (TTL, enable/disable)
    - Response formatting options
    - Rate limiting configuration
    - Logging settings
  - **Methods**:
    - `get_collection_for_type(doc_type)`: Get collection name for document type
    - `get_all_collection_names()`: List all collection names
    - `validate()`: Validate configuration parameters
    - `to_dict()`: Convert to dictionary representation

**Key Features**:
- Environment variable overrides for all settings
- Validation of configuration parameters
- Default values matching existing chunking strategies
- Support for future expansion (Congress, Federal Register)

---

### 5. `src/governmentreporter/server.py`

**Purpose**: Main entry point script for running the MCP server.

**Functions**:
- `setup_logging(log_level)`: Configure logging for the server
- `main(config)`: Async main function that:
  - Validates environment (OpenAI API key)
  - Creates and initializes MCP server
  - Handles signals for graceful shutdown
  - Manages server lifecycle
- `run_server()`: Synchronous wrapper for async main

**Key Features**:
- Command-line executable (`python -m governmentreporter.server`)
- Signal handling for graceful shutdown (SIGINT, SIGTERM)
- Environment validation before startup
- Comprehensive logging of server status
- Error handling with informative messages

---

### 6. `src/governmentreporter/server/__init__.py`

**Purpose**: Module initialization and exports for the server package.

**Exports**:
- Server classes: `GovernmentReporterMCP`, `ServerConfig`
- Handler functions: All 5 MCP tool handlers
- Utilities: `QueryProcessor`, `get_config()`, `set_config()`
- Helper: `create_and_run_server`

---

## MCP Tools Exposed

### 1. `search_government_documents`
- **Purpose**: Primary semantic search across all document types
- **Input**: query (required), document_types (optional), limit (optional)
- **Output**: Ranked chunks with text and metadata

### 2. `search_scotus_opinions`
- **Purpose**: SCOTUS-specific search with legal filters
- **Input**: query, opinion_type, justice, date range
- **Output**: Legal opinion chunks with citations and holdings

### 3. `search_executive_orders`
- **Purpose**: EO-specific search with policy filters
- **Input**: query, president, agencies, policy topics, date range
- **Output**: Policy chunks with agency impacts and authorities

### 4. `get_document_by_id`
- **Purpose**: Retrieve specific document or chunk
- **Input**: document_id, collection, full_document flag
- **Output**: Complete chunk or full document from API

### 5. `list_collections`
- **Purpose**: Show available collections and statistics
- **Input**: None
- **Output**: Collection names, counts, and capabilities

## Data Flow

### Query Processing Flow
1. **LLM sends MCP tool request** → MCP Server receives via protocol
2. **Server routes to appropriate handler** based on tool name
3. **Handler validates arguments** and builds search parameters
4. **Generate query embedding** using `processors/embeddings.py`
5. **Search Qdrant** with filters using `database/qdrant.py`
6. **Format results** using `QueryProcessor` class
7. **Return formatted text** to LLM via MCP protocol
8. **LLM uses chunks** in context window for response generation

### Chunk Retrieval Details
- Chunks are retrieved from Qdrant with similarity scores
- Each chunk contains 600-800 tokens (SCOTUS) or 300-400 tokens (EO)
- Metadata provides context (case name, section, justice, etc.)
- Results are ranked by relevance score
- Formatted for readability with clear structure

## Integration with Existing Code

### Reused Components
- **`database/qdrant.py`**: All vector search operations
- **`processors/embeddings.py`**: Query embedding generation
- **`apis/court_listener.py`**: Optional full SCOTUS document retrieval
- **`apis/federal_register.py`**: Optional full EO retrieval
- **`utils/config.py`**: OpenAI API key management
- **Metadata schemas**: Existing Pydantic models for validation

### Modified Files
- **`pyproject.toml`**: Added `mcp>=1.0.0` dependency and server package

## Running the Server

### Command Line
```bash
# Using uv
uv run python -m governmentreporter.server

# Direct Python
python -m governmentreporter.server

# As script
./src/governmentreporter/server.py
```

### Programmatic
```python
import asyncio
from governmentreporter.server import GovernmentReporterMCP, ServerConfig

async def run():
    config = ServerConfig(default_search_limit=20)
    server = GovernmentReporterMCP(config)
    await server.initialize()
    await server.start()

asyncio.run(run())
```

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your-key-here

# Optional
MCP_SERVER_NAME="Custom MCP Server"
MCP_LOG_LEVEL=DEBUG
MCP_DEFAULT_SEARCH_LIMIT=15
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Key Design Decisions

### 1. Chunk-Based Retrieval
- Returns relevant chunks (not full documents) by default
- Chunks preserve context with hierarchical structure
- Optional full document retrieval available via API

### 2. Specialized Tools
- Separate tools for SCOTUS and EO allow targeted searches
- Document-type-specific metadata filtering
- Maintains flexibility for general cross-collection search

### 3. Rich Formatting
- Structured output optimized for LLM parsing
- Preserves legal citations and document structure
- Includes relevance scores for transparency

### 4. Async Architecture
- Full async/await support for scalability
- Graceful shutdown handling
- Signal management for production deployment

### 5. Configuration Flexibility
- Environment variable overrides for all settings
- Dataclass configuration for type safety
- Validation to catch configuration errors early

## Future Enhancements

### Potential Additions
1. **Caching Layer**: Cache frequent queries and embeddings
2. **Streaming Responses**: Stream large result sets
3. **Query Expansion**: Automatic query enhancement
4. **Reranking**: Post-retrieval result reranking
5. **Additional Collections**: Congress, Federal Register support
6. **Metrics/Monitoring**: Usage statistics and performance metrics
7. **Authentication**: API key or token-based access control
8. **Rate Limiting**: Prevent abuse and manage load

### Expansion Points
- New document types can be added to `collections` mapping
- Additional tools can be registered in `mcp_server.py`
- Custom formatters can be added to `query_processor.py`
- New handlers can be created in `handlers.py`

## Summary

The MCP server implementation provides a clean, extensible interface between LLMs and your GovernmentReporter RAG system. It leverages all existing infrastructure while adding a protocol layer that enables LLMs to perform semantic search and retrieve relevant government document chunks for augmented generation. The modular design allows for easy expansion and customization while maintaining compatibility with the existing codebase.