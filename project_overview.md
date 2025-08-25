# GovernmentReporter Project Overview

This document provides a comprehensive overview of every file in the GovernmentReporter project, detailing their purpose, functionality, and how they interact with each other.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Source Code (`src/`) Analysis](#source-code-src-analysis)
3. [Scripts (`scripts/`) Analysis](#scripts-scripts-analysis)
4. [File Interactions and Data Flow](#file-interactions-and-data-flow)
5. [Component Dependencies](#component-dependencies)

---

## Project Structure

GovernmentReporter is a Python library for retrieving, processing, and storing US federal government publications in a Qdrant vector database for retrieval augmented generation (RAG). The system uses hierarchical document chunking to break down complex legal documents, stores semantic embeddings and metadata in Qdrant, and can retrieve current document text on-demand from government APIs.

```
src/governmentreporter/
├── __init__.py                      # Package initialization
├── apis/                           # Government API clients
├── database/                       # Database integration
├── metadata/                       # AI-powered metadata generation
├── processors/                     # Document processing pipeline
│   ├── base_bulk.py               # Base class for bulk processors
│   ├── scotus_bulk.py             # SCOTUS bulk processor
│   └── executive_order_bulk.py    # Executive Order bulk processor
└── utils/                          # Shared utilities

scripts/
├── download_scotus_bulk.py         # SCOTUS opinion bulk processor (with date range support)
└── process_executive_orders.py     # Executive order bulk processor
```

---

## Source Code (`src/`) Analysis

### Core Module Files

#### `src/governmentreporter/__init__.py`
- **Purpose**: Package initialization and version definition
- **Contents**: Defines `__version__ = "0.1.0"` and package docstring
- **Role**: Entry point for the GovernmentReporter package

[REMOVED - MCP server no longer part of project]

### API Clients (`src/governmentreporter/apis/`)

#### `src/governmentreporter/apis/__init__.py`
- **Purpose**: API module initialization
- **Exports**: CourtListenerClient, FederalRegisterClient

#### `src/governmentreporter/apis/base.py`
- **Purpose**: Abstract base classes for government API clients
- **Key Components**:
  - `Document` dataclass: Standard document representation
  - `GovernmentAPIClient` abstract class: Common API client interface
- **Features**: Rate limiting, date validation, unified document retrieval interface

#### `src/governmentreporter/apis/court_listener.py`
- **Purpose**: CourtListener API integration for Supreme Court opinions
- **Key Methods**:
  - `get_opinion(opinion_id)`: Fetch specific opinion
  - `list_scotus_opinions(since_date, until_date)`: Paginate through SCOTUS opinions with date range support
  - `get_scotus_opinion_count(since_date, until_date)`: Count opinions in date range
  - `get_opinion_cluster()`: Fetch case metadata
  - `extract_basic_metadata()`: Parse opinion metadata
- **Features**: Rate limiting (0.1s delay), bluebook citation building, date range filtering
- **Data Source**: https://www.courtlistener.com/api/rest/v4

#### `src/governmentreporter/apis/federal_register.py`
- **Purpose**: Federal Register API integration for Executive Orders
- **Key Methods**:
  - `list_executive_orders()`: Paginate through executive orders by date range
  - `get_executive_order()`: Fetch specific order
  - `get_executive_order_text()`: Extract raw text content
  - `extract_basic_metadata()`: Parse order metadata
- **Features**: Rate limiting (1.1s delay), exponential backoff retry logic, HTML content cleaning
- **Data Source**: https://www.federalregister.gov/api/v1

### Database Integration (`src/governmentreporter/database/`)

#### `src/governmentreporter/database/__init__.py`
- **Purpose**: Database module initialization
- **Exports**: QdrantDBClient

#### `src/governmentreporter/database/qdrant_client.py`
- **Purpose**: Qdrant integration for vector storage
- **Key Methods**:
  - `get_or_create_collection()`: Collection management
  - `store_document()`: Store document with embeddings and metadata
  - `get_document_by_id()`: Retrieve specific document
  - `list_collections()`: Collection management
- **Features**: Metadata storage with payload support, persistent storage
- **Storage**: Local Qdrant instance at `./qdrant_db`

### Metadata Generation (`src/governmentreporter/metadata/`)

#### `src/governmentreporter/metadata/__init__.py`
- **Purpose**: Metadata module initialization
- **Exports**: GPT5MetadataGenerator

#### `src/governmentreporter/metadata/gpt5_generator.py`
- **Purpose**: AI-powered legal metadata extraction using OpenAI GPT-5-nano
- **Key Methods**:
  - `extract_legal_metadata()`: Extract comprehensive legal metadata from court opinions
  - `_create_legal_metadata_prompt()`: Structured prompt for legal analysis
  - `_validate_legal_metadata()`: Clean and validate extracted metadata
- **Extracted Fields**: legal_topics, key_legal_questions, constitutional_provisions, statutes_interpreted, holding, procedural_outcome, vote_breakdown
- **Features**: Robust error handling, JSON parsing with markdown fence removal

### Document Processors (`src/governmentreporter/processors/`)

#### `src/governmentreporter/processors/__init__.py`
- **Purpose**: Processors module initialization
- **Exports**: SCOTUSBulkProcessor, SCOTUSOpinionProcessor, ExecutiveOrderBulkProcessor, ExecutiveOrderProcessor

#### `src/governmentreporter/processors/base.py`
- **Purpose**: Abstract base class for document processors
- **Key Components**:
  - `ProcessedChunk` dataclass: Represents processed document chunk with embedding
  - `BaseDocumentProcessor` abstract class: Common processing interface
- **Key Methods**:
  - `process_document()`: Abstract method for document processing
  - `store_chunks()`: Store processed chunks in Qdrant
  - `process_and_store()`: Complete processing pipeline
- **Features**: Integrated embedding generation, error handling, progress tracking

#### `src/governmentreporter/processors/base_bulk.py`
- **Purpose**: Abstract base class for bulk processors (NEW)
- **Key Components**:
  - `BaseBulkProcessor` abstract class: Shared functionality for bulk processing
- **Key Methods**:
  - `process_documents()`: Main processing loop with progress tracking
  - `_save_progress()`, `_load_progress()`: Progress persistence
  - `_log_error()`: Error logging
  - Abstract methods: `_process_single_document()`, `get_documents_iterator()`, `get_total_count()`
- **Features**: Resumable operations, progress tracking, error recovery, rate limiting

#### `src/governmentreporter/processors/scotus_bulk.py`
- **Purpose**: Bulk processing system for all SCOTUS opinions (inherits from BaseBulkProcessor)
- **Key Features**:
  - Date range support (since_date and until_date parameters)
  - Progress tracking with resumable operations
  - Error logging and retry mechanisms
  - Rate limiting and API pagination
  - Statistics reporting
- **Key Methods**:
  - `process_all_opinions()`: Process opinions within date range
  - `get_total_count()`: Get opinion count for date range
  - `get_processing_stats()`: Progress statistics
  - Implements abstract methods from BaseBulkProcessor
- **Data Storage**: Progress files, error logs in configurable output directory

#### `src/governmentreporter/processors/scotus_opinion_chunker.py`
- **Purpose**: Hierarchical chunking and metadata processing for SCOTUS opinions
- **Key Components**:
  - `SCOTUSOpinionChunker`: Hierarchical text chunking by opinion type and sections
  - `SCOTUSOpinionProcessor`: Complete processing pipeline
  - `OpinionChunk`: Chunk representation with metadata
  - `ProcessedOpinionChunk`: Complete processed chunk with all metadata
- **Chunking Strategy**:
  1. Split by opinion type (syllabus, majority, concurring, dissenting)
  2. Detect sections within each opinion type
  3. Chunk within sections respecting paragraph boundaries
  4. Target 600 tokens, max 800 tokens per chunk
- **Features**: Token counting, justice attribution, section detection, integrated metadata

#### `src/governmentreporter/processors/executive_order_bulk.py`
- **Purpose**: Bulk processing system for Executive Orders (inherits from BaseBulkProcessor)
- **Key Features**:
  - Date range processing (required start_date and end_date)
  - Duplicate detection (both progress file and database)
  - Progress tracking and error logging
  - Statistics reporting
- **Key Methods**:
  - `process_executive_orders()`: Process orders in date range
  - `get_processing_stats()`: Progress statistics
  - `_check_if_exists_in_db()`: Duplicate detection
  - Implements abstract methods from BaseBulkProcessor
- **Differences from SCOTUS**: Smaller save interval (5 vs 10), database duplicate checking

#### `src/governmentreporter/processors/executive_order_chunker.py`
- **Purpose**: Hierarchical chunking and metadata processing for Executive Orders
- **Key Components**:
  - `ExecutiveOrderChunker`: Hierarchical text chunking by document structure
  - `ExecutiveOrderProcessor`: Complete processing pipeline
  - `ExecutiveOrderMetadataGenerator`: Specialized metadata extraction
  - `ExecutiveOrderChunk`: Chunk representation
  - `ProcessedExecutiveOrderChunk`: Complete processed chunk
- **Chunking Strategy**:
  1. Extract header block (title, authority, preamble)
  2. Detect and process sections (Sec. 1, Sec. 2, etc.)
  3. Handle subsections within sections
  4. Extract tail block (signature, filing info)
  5. Add overlap between consecutive chunks
  - Target 300 tokens, max 400 tokens per chunk (smaller than SCOTUS)
- **Metadata Fields**: summary, policy_topics, impacted_agencies, legal_authorities, executive_orders_referenced/revoked/amended, economic_sectors

### Utilities (`src/governmentreporter/utils/`)

#### `src/governmentreporter/utils/__init__.py`
- **Purpose**: Utilities module initialization and common functions
- **Exports**: All configuration functions, OpenAIEmbeddingsClient, build_bluebook_citation, get_logger
- **Features**: Centralized logger configuration

#### `src/governmentreporter/utils/config.py`
- **Purpose**: Environment variable configuration management
- **Functions**:
  - `get_court_listener_token()`: Required Court Listener API token
  - `get_federal_register_token()`: Optional Federal Register token (planned)
  - `get_congress_gov_token()`: Optional Congress.gov token (planned)
  - `get_openai_api_key()`: Required OpenAI API key
- **Features**: Environment variable validation with helpful error messages

#### `src/governmentreporter/utils/embeddings.py`
- **Purpose**: OpenAI embeddings generation using text-embedding-3-small model
- **Key Methods**:
  - `generate_embedding()`: Generate semantic embeddings for text
- **Features**: Text truncation (32K chars), retrieval-optimized embeddings
- **Model**: OpenAI's text-embedding-3-small for cost-effective embeddings

#### `src/governmentreporter/utils/citations.py`
- **Purpose**: Legal citation formatting utilities
- **Key Functions**:
  - `build_bluebook_citation()`: Convert CourtListener data to bluebook format
- **Output Format**: "601 U.S. 416 (2024)" style citations
- **Features**: Primary citation detection, year extraction

---

## Scripts (`scripts/`) Analysis

### `scripts/download_scotus_bulk.py`
- **Purpose**: Command-line script for bulk SCOTUS opinion processing
- **Key Features**:
  - Command-line argument parsing
  - Integration with SCOTUSBulkProcessor
  - Date range support (NEW: --until-date parameter)
  - Statistics and count-only modes
  - Progress tracking and error handling
- **Arguments**:
  - `--output-dir`: Progress/error log directory
  - `--since-date`: Start date for processing (default: 1900-01-01)
  - `--until-date`: End date for processing (optional, NEW)
  - `--max-opinions`: Limit processing count
  - `--rate-limit-delay`: API rate limiting
  - `--collection-name`: Qdrant collection
  - `--count-only`: Show count without processing
  - `--stats`: Show current statistics
- **Usage**: `uv run python scripts/download_scotus_bulk.py --since-date 2020-01-01 --until-date 2024-12-31`

### `scripts/process_executive_orders.py`
- **Purpose**: Command-line script for Executive Order processing
- **Key Features**:
  - Date range processing (required start and end dates)
  - Integration with ExecutiveOrderBulkProcessor
  - Statistics mode
  - Comprehensive error handling and validation
- **Arguments**:
  - `start_date` (required): Start date in YYYY-MM-DD format
  - `end_date` (required): End date in YYYY-MM-DD format
  - `--output-dir`: Progress/error log directory
  - `--max-orders`: Limit processing count
  - `--collection-name`: Qdrant collection
  - `--stats`: Show statistics without processing
- **Usage**: `uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31`

---

## File Interactions and Data Flow

### 1. Script → Processor → Components Flow

#### SCOTUS Processing Flow:
```
scripts/download_scotus_bulk.py
    ↓ imports and initializes
src/governmentreporter/processors/scotus_bulk.py (SCOTUSBulkProcessor)
    ↓ uses for individual processing
src/governmentreporter/processors/scotus_opinion_chunker.py (SCOTUSOpinionProcessor)
    ↓ coordinates these components:
    ├── src/governmentreporter/apis/court_listener.py (CourtListenerClient)
    ├── src/governmentreporter/metadata/gpt5_generator.py (GPT5MetadataGenerator)
    ├── src/governmentreporter/utils/embeddings.py (OpenAIEmbeddingsClient)
    └── src/governmentreporter/database/qdrant_client.py (QdrantDBClient)
```

#### Executive Order Processing Flow:
```
scripts/process_executive_orders.py
    ↓ imports and initializes
src/governmentreporter/processors/executive_order_bulk.py (ExecutiveOrderBulkProcessor)
    ↓ uses for individual processing
src/governmentreporter/processors/executive_order_chunker.py (ExecutiveOrderProcessor)
    ↓ coordinates these components:
    ├── src/governmentreporter/apis/federal_register.py (FederalRegisterClient)
    ├── src/governmentreporter/processors/executive_order_chunker.py (ExecutiveOrderMetadataGenerator)
    ├── src/governmentreporter/utils/embeddings.py (OpenAIEmbeddingsClient)
    └── src/governmentreporter/database/qdrant_client.py (QdrantDBClient)
```

[REMOVED - MCP server integration no longer part of project]

### 3. Configuration and Utilities Flow

All components depend on:
```
src/governmentreporter/utils/config.py
    ↓ provides API keys/tokens to
    ├── APIs (court_listener.py, federal_register.py)
    ├── Metadata generators (gpt5_generator.py)
    └── Embedding clients (embeddings.py)

src/governmentreporter/utils/__init__.py
    ↓ provides logging to
    └── All processors and bulk processors
```

### 4. Data Processing Pipeline

#### For SCOTUS Opinions:
1. **Fetch**: CourtListenerClient retrieves opinion data and cluster metadata
2. **Chunk**: SCOTUSOpinionChunker hierarchically splits text by opinion type → sections → paragraphs
3. **Metadata**: GPT5MetadataGenerator extracts legal metadata using AI
4. **Embed**: OpenAIEmbeddingsClient generates semantic embeddings
5. **Store**: QdrantDBClient stores chunks with embeddings and metadata
6. **Search**: Applications can query Qdrant for semantic search

#### For Executive Orders:
1. **Fetch**: FederalRegisterClient retrieves order data and raw text
2. **Chunk**: ExecutiveOrderChunker hierarchically splits text by header → sections → subsections → tail
3. **Metadata**: ExecutiveOrderMetadataGenerator extracts policy metadata using AI
4. **Embed**: OpenAIEmbeddingsClient generates semantic embeddings
5. **Store**: QdrantDBClient stores chunks with embeddings and metadata

---

## Component Dependencies

### External API Dependencies:
- **CourtListener API**: SCOTUS opinion data (`court_listener.py`)
- **Federal Register API**: Executive order data (`federal_register.py`)
- **OpenAI API**: Metadata extraction and embeddings (`gpt5_generator.py`, `embeddings.py`)

### Internal Component Dependencies:

#### High-Level Components:
- **Scripts** depend on bulk processors
- **Bulk processors** depend on individual document processors
- **Document processors** depend on APIs, metadata generators, embeddings, and database

#### Utility Dependencies:
- **All components** depend on `utils/config.py` for API credentials
- **Processors and scripts** depend on `utils/__init__.py` for logging
- **Citation formatting** uses `utils/citations.py`

#### Base Class Dependencies:
- **All API clients** inherit from `apis/base.py`
- **All document processors** inherit from `processors/base.py`
- **Bulk processors** inherit from `processors/base_bulk.py` (NEW)

### Database Dependencies:
- **All processors** store data via `database/qdrant_client.py`
- **Qdrant** provides persistent vector storage for embeddings and metadata
- **Applications** can query Qdrant directly for semantic search

This architecture enables a modular, scalable system where each component has clear responsibilities and well-defined interfaces, allowing for easy extension to additional government data sources while maintaining consistency in processing and storage.
