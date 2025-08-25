# GovernmentReporter Program Structure Overview

## Project Overview

GovernmentReporter is an MCP (Model Context Protocol) server that provides LLMs with access to US federal government publications through RAG (Retrieval Augmented Generation). The system stores semantic embeddings and metadata in Qdrant (a vector database), then retrieves current document text on-demand from government APIs.

## Architecture Overview

```
src/governmentreporter/
├── __init__.py                 # Main package initialization
├── apis/                        # Government API client implementations
│   ├── __init__.py
│   ├── base.py                 # Abstract base classes for API clients
│   ├── court_listener.py       # Court Listener API client (SCOTUS opinions)
│   └── federal_register.py     # Federal Register API client (Executive Orders)
├── database/                    # Vector database integration
│   ├── __init__.py
│   └── qdrant_client.py        # Qdrant vector database operations
└── utils/                       # Shared utilities and helpers
    ├── __init__.py             # Package initializer with logging setup
    ├── citations.py            # Bluebook citation formatting
    └── config.py               # Environment variable management
```

## Core Data Flow

### 1. Document Indexing Pipeline
```
Government API → Fetch Documents → Generate Embeddings → Store in Qdrant
                                 ↓
                          Extract Metadata
```

### 2. Query/Retrieval Pipeline  
```
User Query → Generate Query Embedding → Search Qdrant → Retrieve Document IDs
                                                      ↓
                                            Fetch Fresh Content from APIs
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

### 3. Utils Module (`src/governmentreporter/utils/`)

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

#### `__init__.py` - Package Initialization and Logging
- **Purpose**: Centralized logging configuration and utility imports
- **Key Functions**:
  - `setup_logging()`: Configures logging from YAML file
  - `get_logger()`: Returns configured logger instances
- **Exports**: Makes key utilities available for import

## Component Interactions

### 1. API Client Hierarchy
```
GovernmentAPIClient (abstract base)
    ├── CourtListenerClient (concrete implementation)
    └── FederalRegisterClient (concrete implementation)
```

### 2. Data Flow Between Components

#### Document Storage Flow:
1. **API Client** fetches document from government source
2. **API Client** creates standardized `Document` object
3. **Embedding generation** (not in src, but would use OpenAI)
4. **QdrantDBClient** stores document + embedding + metadata

#### Document Retrieval Flow:
1. Query embedding generated (not in src)
2. **QdrantDBClient** performs semantic search
3. Returns document IDs and scores
4. **API Client** fetches fresh content using document IDs
5. Returns updated `Document` objects

### 3. Configuration Dependencies
```
config.py provides credentials to:
    ├── court_listener.py (needs Court Listener token)
    └── (future) OpenAI embedding client (needs OpenAI key)
```

### 4. Utility Usage
- **citations.py** used by `court_listener.py` for Bluebook formatting
- **logging** from `utils/__init__.py` used by all modules for operation tracking

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
4. Advanced metadata extraction
5. Caching layers for frequently accessed documents

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

## Testing Considerations

While tests are not in the `src` folder, the architecture supports:
- Unit testing via dependency injection
- Mock API responses for testing
- Abstract base classes enable test doubles
- Clear separation of concerns for isolated testing