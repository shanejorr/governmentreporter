# GovernmentReporter Program Structure Overview

## Project Overview

GovernmentReporter is an MCP (Model Context Protocol) server that provides LLMs with access to US federal government publications through RAG (Retrieval Augmented Generation). The system stores semantic embeddings and metadata in Qdrant (a vector database), then retrieves current document text on-demand from government APIs.

## Architecture Overview

```
src/governmentreporter/
├── __init__.py                 # Main package initialization
├── server.py                   # MCP server entry point and main runner
├── apis/                        # Government API client implementations
│   ├── __init__.py
│   ├── base.py                 # Abstract base classes for API clients
│   ├── court_listener.py       # Court Listener API client (SCOTUS opinions)
│   └── federal_register.py     # Federal Register API client (Executive Orders)
├── database/                    # Vector database integration
│   ├── __init__.py
│   ├── qdrant_client.py        # Qdrant vector database operations
│   └── ingestion.py            # Specialized ingestion client with batch operations
├── processors/                  # Document processing and transformation
│   ├── __init__.py             # Package exports and documentation
│   ├── build_payloads.py       # Main orchestration for document processing
│   ├── chunking.py             # Hierarchical document chunking algorithms
│   ├── embeddings.py           # OpenAI embedding generation utilities
│   ├── llm_extraction.py       # GPT-5-nano metadata extraction
│   └── schema.py               # Pydantic models for metadata validation
├── server/                      # MCP server implementation for LLM integration
│   ├── __init__.py             # Server module exports and version info
│   ├── mcp_server.py           # Main MCP server class and lifecycle management
│   ├── handlers.py             # Tool handlers for MCP requests (5 tools)
│   ├── query_processor.py      # Result formatting optimized for LLM consumption
│   └── config.py               # Server configuration with environment variables
└── utils/                       # Shared utilities and helpers
    ├── __init__.py             # Package initializer with logging setup
    ├── citations.py            # Bluebook citation formatting
    ├── config.py               # Environment variable management
    └── monitoring.py           # Performance monitoring and progress tracking
```

## Core Data Flow

### 1. Document Indexing Pipeline
```
Government API → Fetch Documents → Chunk Documents → Extract Metadata
                                         ↓                ↓
                                  Generate Embeddings → Store in Qdrant
```

### 2. MCP Query/Retrieval Pipeline
```
LLM Tool Call → MCP Server → Generate Query Embedding → Search Qdrant → Retrieve Chunks
                    ↓                                                       ↓
            Route to Handler                                         Format Results
                    ↓                                                       ↓
            Validate Arguments                                  Return to LLM Context
```

### 3. Optional Full Document Retrieval Pipeline
```
Chunk Results → Extract Document IDs → Fetch Fresh Content from APIs → Return Full Document
```

## Module Details

### 1. APIs Module (`src/governmentreporter/apis/`)

This module provides client implementations for various government data sources.

#### `base.py` - Abstract Base Classes
- **Purpose**: Defines the standard interface that all government API clients must implement
- **Key Components**:
  - `Document` dataclass: Standardized representation of government documents
    - Fields: id, title, date, type, source, content, metadata, url
  - `GovernmentAPIClient` abstract base class: Template for all API clients
    - Abstract methods: `_get_base_url()`, `_get_rate_limit_delay()`, `search_documents()`, `get_document()`, `get_document_text()`
    - Concrete method: `validate_date_format()` for date validation

#### `court_listener.py` - Court Listener API Client
- **Purpose**: Fetches US federal court opinions, especially Supreme Court decisions
- **Inheritance**: Extends `GovernmentAPIClient`
- **Key Features**:
  - Authentication via API token (from environment variable)
  - Rate limiting (0.1 second delay between requests)
  - Opinion and cluster data retrieval
  - Bluebook citation generation
- **Primary Methods**:
  - `get_opinion(opinion_id)`: Fetches specific opinion by ID
  - `search_documents()`: Searches Supreme Court opinions with filters
  - `get_document()`: Returns standardized Document object
  - `get_opinion_cluster()`: Fetches case-level metadata
  - `list_scotus_opinions()`: Lists opinions with date filtering

#### `federal_register.py` - Federal Register API Client
- **Purpose**: Retrieves executive orders and other presidential documents
- **Inheritance**: Extends `GovernmentAPIClient`
- **Key Features**:
  - No authentication required (public API)
  - Rate limiting (1.1 second delay for 60/minute limit)
  - Exponential backoff retry logic
  - HTML content cleaning
- **Primary Methods**:
  - `_make_request_with_retry()`: Robust HTTP requests with retry logic
  - `get_executive_order_text()`: Fetches and cleans order text
  - `list_executive_orders()`: Lists orders with date filtering
  - `search_documents()`: Searches executive orders
  - `get_document()`: Returns standardized Document object

### 2. Database Module (`src/governmentreporter/database/`)

#### `qdrant_client.py` - Qdrant Vector Database Client
- **Purpose**: Manages document embeddings and metadata in Qdrant vector database
- **Key Features**:
  - Persistent local storage of vectors
  - 1536-dimensional vectors (OpenAI text-embedding-3-small)
  - Cosine similarity for semantic search
  - Metadata filtering and querying
- **Primary Methods**:
  - `get_or_create_collection()`: Manages collections (like database tables)
  - `store_document()`: Stores document with embedding and metadata
  - `get_document_by_id()`: Retrieves specific document
  - `semantic_search()`: Performs vector similarity search with filters
  - `batch_upsert()`: Bulk document storage
  - `list_collections()`: Lists available collections
  - `delete_collection()`: Removes collections

#### `ingestion.py` - Specialized Ingestion Client
- **Purpose**: High-performance batch ingestion of documents into Qdrant
- **Inheritance**: Uses QdrantDBClient for core operations
- **Key Features**:
  - Collection initialization with proper vector configuration
  - Duplicate detection to avoid redundant storage
  - Batch upsert operations with progress callbacks
  - Deterministic ID generation for document chunks
  - Collection statistics and monitoring
- **Primary Methods**:
  - `ensure_collection_exists()`: Creates collections with cosine distance metric
  - `document_exists()`: Checks for existing documents before insertion
  - `batch_upsert_documents()`: Efficient bulk insertion with progress tracking
  - `_generate_chunk_id()`: Creates consistent MD5-based chunk IDs
  - `get_collection_stats()`: Returns collection metrics and status

### 3. Processors Module (`src/governmentreporter/processors/`)

This module provides document processing capabilities for transforming raw government documents into structured, searchable chunks with rich metadata.

#### `schema.py` - Pydantic Data Models
- **Purpose**: Defines strict data validation schemas using Pydantic
- **Key Models**:
  - `SupremeCourtMetadata`: SCOTUS-specific metadata (legal topics, constitutional provisions, holdings)
  - `ExecutiveOrderMetadata`: EO-specific metadata (policy topics, agencies, economic sectors)
  - `ChunkMetadata`: Common chunk data (text, type, indices)
  - `QdrantPayload`: Complete payload structure for vector database
- **Validation**: Ensures data integrity with type checking and constraints

#### `chunking.py` - Hierarchical Document Chunking
- **Purpose**: Intelligently splits documents by their natural structure with configurable overlap
- **Configurations**:
  - `ChunkingConfig`: Dataclass for per-document-type chunking parameters
  - `SCOTUS_CFG`: Min 500, target 600, max 800 tokens, 15% overlap ratio
  - `EO_CFG`: Min 240, target 340, max 400 tokens, 10% overlap ratio
  - Environment overrides supported (e.g., `RAG_SCOTUS_TARGET_TOKENS`)
- **Key Functions**:
  - `chunk_supreme_court_opinion()`: Splits SCOTUS opinions by type, sections, and paragraphs
    - Detects syllabus, majority, concurring, dissenting opinions
    - Parses Roman numeral sections (I, II, III) and subsections (A, B, C)
    - Uses sliding window with 15% overlap within sections
  - `chunk_executive_order()`: Splits EOs by header, sections, subsections, tail
    - Identifies numbered sections (Sec. 1, Sec. 2) and lettered subsections
    - Preserves section titles and structure
    - NEVER creates overlap across section boundaries
    - 10% overlap applied only within same section
  - `chunk_text_with_tokens()`: Core sliding window implementation
    - Configurable min/target/max tokens and overlap
    - Merges small remainder chunks when < min_tokens
    - Adds `chunk_token_count` metadata for debugging

#### `embeddings.py` - OpenAI Embedding Generation
- **Purpose**: Generates vector embeddings from text using OpenAI's models
- **Key Features**:
  - Uses text-embedding-3-small model (1536 dimensions)
  - Batch processing for efficiency
  - Retry logic with exponential backoff
  - Fallback to individual generation on batch failures
- **Primary Methods**:
  - `generate_embedding()`: Creates single text embedding with retries
  - `generate_batch_embeddings()`: Efficient batch embedding generation
- **Error Handling**: Falls back to zero vectors on complete failure

#### `llm_extraction.py` - AI-Powered Metadata Generation
- **Purpose**: Uses GPT-5-nano to extract rich metadata from document text
- **Key Functions**:
  - `generate_scotus_llm_fields()`: Extracts legal metadata from Supreme Court opinions
    - Legal topics and key questions
    - Constitutional provisions and statutes cited
    - Holdings and vote breakdowns
  - `generate_eo_llm_fields()`: Extracts policy metadata from Executive Orders
    - Policy summaries and topics
    - Impacted agencies and legal authorities
    - Economic sectors affected
- **Implementation**: Structured prompts with JSON output for reliable extraction

#### `build_payloads.py` - Processing Orchestration
- **Purpose**: Main entry point that coordinates all processing steps
- **Key Function**:
  - `build_payloads_from_document()`: Orchestrates complete processing pipeline
    - Accepts Document object from API clients
    - Routes to appropriate chunking algorithm based on document type
    - Generates metadata using LLM extraction
    - Validates data with Pydantic schemas
    - Returns Qdrant-ready payloads
- **Flow**: Document → Chunk → Extract Metadata → Validate → Return Payloads

### 4. Utils Module (`src/governmentreporter/utils/`)

#### `config.py` - Configuration Management
- **Purpose**: Secure access to API credentials via environment variables
- **Key Functions**:
  - `get_court_listener_token()`: Returns Court Listener API token
  - `get_openai_api_key()`: Returns OpenAI API key
- **Security**: Never hardcodes credentials, reads from environment

#### `citations.py` - Citation Formatting
- **Purpose**: Formats legal citations according to Bluebook standards
- **Key Function**:
  - `build_bluebook_citation()`: Creates formatted citations like "410 U.S. 113 (1973)"
  - Handles Court Listener's citation data structure
  - Validates and formats volume, reporter, page, and year

#### `monitoring.py` - Performance Monitoring
- **Purpose**: Tracks and reports on batch operation performance
- **Key Features**:
  - Real-time progress bars with ETA calculation
  - Success/failure rate tracking
  - Throughput and timing statistics
  - Human-readable duration formatting
- **Primary Methods**:
  - `start()`: Initializes monitoring session
  - `record_document()`: Tracks individual document processing
  - `get_statistics()`: Returns comprehensive performance metrics
  - `print_progress()`: Displays visual progress bar with ETA
  - `_format_duration()`: Converts seconds to readable format (2h 15m 30s)
- **Metrics Tracked**: Elapsed time, documents processed/failed, success rate, throughput

#### `__init__.py` - Package Initialization and Logging
- **Purpose**: Centralized logging configuration and utility imports
- **Key Functions**:
  - `setup_logging()`: Configures logging from YAML file
  - `get_logger()`: Returns configured logger instances
- **Exports**: Makes key utilities available for import

### 5. Server Module (`src/governmentreporter/server/`)

This module implements the MCP (Model Context Protocol) server that enables LLMs to semantically search government documents and retrieve relevant chunks for context-aware responses.

#### `mcp_server.py` - Main MCP Server Implementation
- **Purpose**: Core MCP server that manages tool registration and request handling
- **Key Components**:
  - `GovernmentReporterMCP` class: Main server implementation
    - Manages server lifecycle (initialize, start, shutdown)
    - Registers 5 MCP tools for LLM interaction
    - Handles async operations and graceful shutdown
    - Provides connection management for Qdrant
  - `create_and_run_server()`: Convenience function for server startup
- **MCP Tools Registered**:
  - `search_government_documents`: Cross-collection semantic search
  - `search_scotus_opinions`: SCOTUS-specific search with legal filters
  - `search_executive_orders`: Executive Order search with policy filters
  - `get_document_by_id`: Retrieve specific document/chunk by ID
  - `list_collections`: Show available collections and statistics

#### `handlers.py` - Tool Handlers for MCP Requests
- **Purpose**: Contains handler functions for each MCP tool exposed to LLMs
- **Key Functions**:
  - `handle_search_government_documents()`: Main semantic search across collections
  - `handle_search_scotus_opinions()`: SCOTUS search with opinion type, justice, date filters
  - `handle_search_executive_orders()`: EO search with president, agency, policy filters
  - `handle_get_document_by_id()`: Document/chunk retrieval by ID
  - `handle_list_collections()`: Collection information and statistics
- **Features**:
  - Generates query embeddings using existing `embeddings.py`
  - Builds Qdrant filter conditions for metadata filtering
  - Handles errors gracefully with informative messages
  - Supports optional full document retrieval from APIs

#### `query_processor.py` - Result Formatting for LLMs
- **Purpose**: Formats search results from Qdrant for optimal LLM consumption
- **Key Components**:
  - `QueryProcessor` class: Main formatting engine
    - `format_search_results()`: General search result formatting
    - `format_scotus_results()`: SCOTUS-specific formatting with legal context
    - `format_eo_results()`: Executive Order formatting with policy context
    - `format_document_chunk()`: Single chunk formatting with metadata
    - `format_collections_list()`: Collection information display
- **Features**:
  - Preserves document structure in formatted output
  - Truncates long chunks to prevent context overflow
  - Emphasizes relevant metadata for each document type
  - Includes relevance scores and proper citations
  - Optimized for LLM parsing and comprehension

#### `config.py` - Server Configuration Management
- **Purpose**: Configuration settings for the MCP server with environment variable support
- **Key Components**:
  - `ServerConfig` dataclass: Comprehensive server configuration
    - Server identification (name, version)
    - Collection mappings (document types to Qdrant collections)
    - Search parameters (limits, defaults)
    - Qdrant connection settings (host, port, API key)
    - Embedding configuration (model, dimensions)
    - Chunking configurations (SCOTUS and EO specific)
    - Caching, rate limiting, and logging settings
- **Features**:
  - Environment variable overrides for all settings
  - Validation of configuration parameters
  - Default values matching existing chunking strategies
  - Support for future expansion (Congress, Federal Register)

#### `__init__.py` - Server Module Exports
- **Purpose**: Module initialization and exports for the server package
- **Exports**:
  - Server classes: `GovernmentReporterMCP`, `ServerConfig`
  - Handler functions: All 5 MCP tool handlers
  - Utilities: `QueryProcessor`, `get_config()`, `set_config()`
  - Helper: `create_and_run_server`

### 6. Main Entry Points

#### `server.py` - MCP Server Entry Point
- **Purpose**: Command-line entry point for running the MCP server
- **Key Functions**:
  - `setup_logging()`: Configure logging for the server
  - `main()`: Async main function that manages server lifecycle
  - `run_server()`: Synchronous wrapper for async main
- **Features**:
  - Command-line executable (`python -m governmentreporter.server`)
  - Signal handling for graceful shutdown (SIGINT, SIGTERM)
  - Environment validation before startup
  - Comprehensive logging of server status
  - Error handling with informative messages

## Component Interactions

### 1. Module Hierarchy
```
GovernmentReporter Package
    ├── APIs Module
    │   ├── GovernmentAPIClient (abstract base)
    │   ├── CourtListenerClient (concrete implementation)
    │   └── FederalRegisterClient (concrete implementation)
    ├── Processors Module
    │   ├── Schema (data validation)
    │   ├── Chunking (document splitting)
    │   ├── Embeddings (vector generation)
    │   ├── LLM Extraction (metadata generation)
    │   └── Build Payloads (orchestration)
    ├── Database Module
    │   ├── QdrantDBClient (vector storage)
    │   └── QdrantIngestionClient (batch ingestion)
    ├── Server Module
    │   ├── GovernmentReporterMCP (main server)
    │   ├── Tool Handlers (5 MCP tools)
    │   ├── QueryProcessor (result formatting)
    │   └── ServerConfig (configuration management)
    ├── Utils Module
    │   ├── Config (credentials)
    │   ├── Citations (formatting)
    │   ├── Monitoring (performance tracking)
    │   └── Logging (operation tracking)
    └── Entry Points
        └── server.py (MCP server runner)
```

### 2. Data Flow Between Components

#### Document Storage Flow:
1. **API Client** fetches document from government source
2. **API Client** creates standardized `Document` object
3. **Processors Module** processes document:
   - **Chunking** splits by natural structure
   - **LLM Extraction** generates metadata
   - **Schema** validates all data
   - **Build Payloads** orchestrates and returns payloads
4. **EmbeddingGenerator** creates vector embeddings via OpenAI API
5. **QdrantIngestionClient** batch stores chunks + embeddings + metadata
6. **PerformanceMonitor** tracks ingestion progress and statistics

#### Document Retrieval Flow (via MCP Server):
1. **LLM** sends tool call request via MCP protocol
2. **MCP Server** routes request to appropriate handler
3. **Handler** validates arguments and generates query embedding
4. **QdrantDBClient** performs semantic search on chunks with filters
5. **QueryProcessor** formats results for LLM consumption
6. **MCP Server** returns formatted chunks to LLM context window
7. **Optional**: API Client fetches fresh full documents if requested

### 3. Configuration Dependencies
```
config.py provides credentials to:
    ├── court_listener.py (needs Court Listener token)
    ├── llm_extraction.py (needs OpenAI key for GPT-5-nano)
    ├── embeddings.py (needs OpenAI key for text-embedding-3-small)
    └── server module (needs OpenAI key for query embeddings)

server/config.py provides server settings:
    ├── Collection mappings (document types to Qdrant collections)
    ├── Search parameters (limits, defaults)
    ├── Qdrant connection settings (host, port, API key)
    ├── Embedding configuration (model, dimensions)
    └── Caching, rate limiting, and logging settings
```

### 4. Module Interactions
- **APIs → Processors**: Documents flow from API clients to processors
- **Processors → Database**: Processed chunks stored in Qdrant
- **Server → Database**: MCP server queries Qdrant for semantic search
- **Server → Processors**: Server uses embeddings module for query vectors
- **Server → APIs**: Optional full document retrieval from government APIs
- **Utils → All**: Config and logging used throughout
- **citations.py** used by `court_listener.py`, processors, and server for Bluebook formatting
- **schema.py** validates data throughout processing pipeline
- **LLMs → Server**: External LLMs interact via MCP protocol

## Key Design Patterns

### 1. Abstract Base Class Pattern
- `GovernmentAPIClient` enforces consistent interface
- All API clients must implement required methods
- Ensures interchangeability of different data sources

### 2. Template Method Pattern
- `GovernmentAPIClient.__init__()` provides common initialization
- Subclasses customize via abstract methods (`_get_base_url()`, etc.)

### 3. Data Class Pattern
- `Document` class provides immutable, type-safe data structure
- Standardizes document representation across different sources

### 4. Repository Pattern
- `QdrantDBClient` abstracts database operations
- Provides high-level interface for vector storage

### 5. Retry Pattern with Exponential Backoff
- `FederalRegisterClient._make_request_with_retry()` handles network failures
- Progressively increases delay between retries

### 6. Pipeline Pattern
- `build_payloads.py` implements processing pipeline
- Each stage transforms data for the next
- Clear separation of concerns

### 7. Strategy Pattern
- Different chunking strategies for different document types
- `chunk_supreme_court_opinion()` vs `chunk_executive_order()`
- Selected based on document type

### 8. Validation Pattern
- Pydantic models ensure data integrity
- Type checking and constraint validation
- Fail-fast approach for invalid data

## Error Handling Strategy

1. **Configuration Errors**: Raise `ValueError` immediately (fail fast)
2. **Network Errors**: Retry with exponential backoff
3. **API Errors**: Log warnings, gracefully degrade functionality
4. **Database Errors**: Log errors, raise exceptions for critical failures

## Logging Architecture

- Centralized configuration via YAML file
- Module-specific log levels
- Separate handlers for different log levels
- Rotating file handlers to manage disk usage

## Future Extension Points

The architecture is designed to easily add:
1. New government API clients (Congress.gov, etc.)
2. Additional document types (federal rules, congressional bills)
3. Cloud database support (remote Qdrant instance)
4. Advanced metadata extraction strategies
5. Caching layers for frequently accessed documents
6. Alternative chunking strategies for new document types
7. Different LLM providers for metadata extraction
8. Additional validation schemas for new metadata types
9. Batch processing optimizations
10. ✅ **COMPLETED**: MCP server implementation for LLM integration

### New MCP Server Extension Points:
11. **Additional MCP Tools**: New tools for specific legal research workflows
12. **Streaming Responses**: Real-time result streaming for large queries
13. **Query Expansion**: Automatic query enhancement and suggestion
14. **Result Reranking**: Post-retrieval result optimization
15. **Caching Layer**: Cache frequent queries and embeddings
16. **Authentication**: API key or token-based access control
17. **Rate Limiting**: Prevent abuse and manage server load
18. **Metrics/Monitoring**: Usage statistics and performance tracking
19. **Multi-LLM Support**: Concurrent support for multiple LLM clients
20. **Custom Formatting**: LLM-specific result formatting strategies

## Security Considerations

1. **Credentials**: All API keys from environment variables
2. **No Hardcoding**: Sensitive data never in source code
3. **Rate Limiting**: Respects API limits to avoid blocks
4. **Error Messages**: Don't expose sensitive information

## Performance Optimizations

1. **Batch Operations**: Bulk storage in Qdrant
2. **Lazy Loading**: Documents fetched only when needed
3. **Memory Efficiency**: Iterator patterns for large result sets
4. **Connection Pooling**: HTTP clients with context managers
5. **Token-Aware Chunking**: Optimized chunk sizes for embedding efficiency
6. **Structured Metadata**: Pydantic models for fast serialization
7. **Parallel Processing**: Ready for concurrent document processing
8. **Smart Overlap**: Minimal overlap in chunks to reduce redundancy

## Testing Considerations

While tests are not in the `src` folder, the architecture supports:
- Unit testing via dependency injection
- Mock API responses for testing
- Abstract base classes enable test doubles
- Clear separation of concerns for isolated testing