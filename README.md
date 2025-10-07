# GovernmentReporter

A Python library and **MCP (Model Context Protocol) server** for retrieving, processing, and storing US federal government publications in a Qdrant vector database for retrieval augmented generation (RAG) using **hierarchical document chunking**.

## Quick Start

```bash
# Install dependencies
uv sync

# Start MCP server for LLM integration
uv run governmentreporter server

# Ingest Supreme Court opinions
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31

# Ingest Executive Orders
uv run governmentreporter ingest eo --start-date 2024-01-01 --end-date 2024-12-31

# View database information
uv run governmentreporter info collections

# Test semantic search
uv run governmentreporter query "environmental regulation"

# Get help
uv run governmentreporter --help
```

## Overview

GovernmentReporter creates a Qdrant vector database storing semantic embeddings and rich metadata for hierarchically chunked US federal Supreme Court opinions and Executive Orders. The system uses **intelligent chunking** to break down documents by their natural structure - Supreme Court opinions by opinion type (syllabus, majority, concurring, dissenting) and sections, Executive Orders by header/sections/subsections/tail - enabling precise legal research and retrieval.

The system includes a Model Context Protocol server that enables Large Language Models (like Claude, GPT-4, etc.) to semantically search government documents and retrieve relevant chunks for context-aware responses.

## Features

### 🧩 Hierarchical Document Chunking
**Supreme Court Opinions:**
- **Opinion Type Separation**: Automatically identifies syllabus, majority, concurring, and dissenting opinions
- **Section-Level Granularity**: Chunks opinions by legal sections (I, II, III) and subsections (A, B, C)
- **Justice Attribution**: Concurring and dissenting opinions properly attributed to specific justices
- **Smart Token Management**: Min 500, target 600, max 800 tokens per chunk with 15% sliding window overlap
- **Overlap Strategy**: Sliding window with 15% overlap for context continuity within sections

**Executive Orders:**
- **Structural Chunking**: Separates header, sections (Sec. 1, Sec. 2), subsections, and signature blocks
- **Section Detection**: Automatically identifies numbered sections and lettered subsections
- **Section Boundary Preservation**: Never creates overlap across section boundaries - each section chunked independently
- **Compact Chunking**: Min 240, target 340, max 400 tokens per chunk with 10% sliding window overlap
- **Intra-Section Overlap**: 10% overlap applied only within same section, preserving regulatory structure

### 📊 Rich Legal Metadata
**Supreme Court Opinions:**
- **Legal Topics**: AI-extracted primary areas of law (Constitutional Law, Administrative Law, etc.)
- **Constitutional Provisions**: Precise citations (Art. I, § 9, cl. 7, First Amendment, etc.)
- **Statutes Interpreted**: Bluebook format citations (12 U.S.C. § 5497, 42 U.S.C. § 1983)
- **Key Legal Questions**: Specific questions the court addressed
- **Court Holdings**: Extracted from syllabus and decisions
- **Vote Breakdown**: Justice voting patterns (9-0, 7-2, etc.)

**Executive Orders:**
- **Policy Summary**: Concise abstracts of executive order purpose
- **Policy Topics**: Topical tags (aviation, regulatory reform, environment, etc.)
- **Impacted Agencies**: Federal agency codes (FAA, EPA, NASA, etc.)
- **Legal Authorities**: U.S. Code and CFR citations in bluebook format
- **EO References**: Related executive orders referenced, revoked, or amended
- **Economic Sectors**: Affected industries and societal sectors

### 🚀 Advanced Capabilities
- **Comprehensive Government Data**: Indexes US Supreme Court opinions and Executive Orders
- **Fresh Data Guarantee**: Retrieves latest document text on-demand from government APIs
- **Semantic Search**: Vector database enables intelligent document discovery at chunk level
- **MCP Server Integration**: Direct LLM access via Model Context Protocol
- **API-First Design**: Reusable library components for custom workflows
- **Bulk Processing**: Automated pipeline for processing large datasets (10,000+ Supreme Court opinions)
- **Resumable Operations**: Progress tracking and error recovery for long-running processes
- **Duplicate Detection**: Smart checking to avoid reprocessing existing documents
- **Programmatic API**: Reusable library components for custom data processing workflows

### 🤖 MCP Server Features
- **5 Specialized Tools**: Search across collections, SCOTUS-specific search, Executive Order search, document retrieval, collection listing
- **Advanced Filtering**: Filter by opinion type, justice, president, agencies, policy topics, date ranges
- **Structured Output**: Results formatted for optimal LLM comprehension with citations and metadata
- **Real-time Search**: Live semantic search with relevance scoring
- **Chunk-level Precision**: Returns relevant document segments with hierarchical context

## Architecture

- **Language**: Python 3.11+
- **Package Manager**: uv (modern Python package manager)
- **Vector Database**: Qdrant (embeddings + metadata only)
- **AI Services**:
  - OpenAI GPT-5-nano for metadata generation
  - OpenAI text-embedding-3-small for semantic embeddings
- **Government APIs**:
  - CourtListener API (Supreme Court opinions)
  - Federal Register API (Executive Orders)
- **Development**: VS Code with Claude Code support
- **Storage**: Qdrant vector database

### Core Modules

- **APIs Module** (`src/governmentreporter/apis/`): Government API clients
  - `base.py`: Abstract base classes for API clients
  - `court_listener.py`: CourtListener API for SCOTUS opinions
  - `federal_register.py`: Federal Register API for Executive Orders

- **CLI Module** (`src/governmentreporter/cli/`): Command-line interface
  - `main.py`: Primary CLI entry point with Click framework
  - `ingest.py`: Document ingestion commands (scotus, eo)
  - `server.py`: MCP server start command
  - `query.py`: Test query command for semantic search

- **Database Module** (`src/governmentreporter/database/`): Qdrant vector storage
  - `qdrant.py`: Core vector database operations
  - `ingestion.py`: High-performance batch ingestion utilities

- **Ingestion Module** (`src/governmentreporter/ingestion/`): Document ingestion pipelines
  - `base.py`: Abstract base class for ingestion pipelines
  - `scotus.py`: Supreme Court opinion ingestion pipeline
  - `executive_orders.py`: Executive Order ingestion pipeline
  - `progress.py`: Progress tracking and resumable operations

- **Processors Module** (`src/governmentreporter/processors/`): Document processing
  - `chunking/`: Hierarchical document chunking algorithms
    - `base.py`: Shared utilities and core chunking algorithm
    - `scotus.py`: Supreme Court-specific chunking with opinion type detection
    - `executive_orders.py`: Executive Order-specific chunking by sections
  - `embeddings.py`: OpenAI embedding generation with batch support
  - `llm_extraction.py`: GPT-5-nano metadata extraction
  - `schema.py`: Pydantic data validation models
  - `build_payloads.py`: Processing orchestration

- **Server Module** (`src/governmentreporter/server/`): MCP server for LLM integration
  - `mcp_server.py`: Main MCP server implementation with tool registration
  - `handlers.py`: Tool handlers for search, retrieval, and collection operations
  - `query_processor.py`: Result formatting optimized for LLM consumption
  - `config.py`: Server configuration with environment variable support
  - `__main__.py`: Server entry point for `python -m governmentreporter.server`

- **Utils Module** (`src/governmentreporter/utils/`): Shared utilities
  - `citations.py`: Bluebook citation formatting
  - `config.py`: Environment variable and credential management
  - `monitoring.py`: Performance monitoring with progress tracking

### Project Structure

```
governmentreporter/
├── src/governmentreporter/
│   ├── apis/                      # Government API clients
│   │   ├── base.py               # Abstract base class
│   │   ├── court_listener.py     # CourtListener API
│   │   └── federal_register.py   # Federal Register API
│   ├── cli/                       # Command-line interface
│   │   ├── main.py               # CLI entry point
│   │   ├── ingest.py             # Ingestion commands
│   │   ├── server.py             # Server command
│   │   └── query.py              # Query command
│   ├── database/                  # Vector database
│   │   ├── qdrant.py             # Qdrant client
│   │   └── ingestion.py          # Batch ingestion
│   ├── ingestion/                 # Ingestion pipelines
│   │   ├── base.py               # Base pipeline class
│   │   ├── scotus.py             # SCOTUS pipeline
│   │   ├── executive_orders.py   # EO pipeline
│   │   └── progress.py           # Progress tracking
│   ├── processors/                # Document processing
│   │   ├── chunking/             # Chunking algorithms
│   │   │   ├── base.py           # Core chunking utilities
│   │   │   ├── scotus.py         # SCOTUS chunking
│   │   │   └── executive_orders.py # EO chunking
│   │   ├── embeddings.py         # Embedding generation
│   │   ├── llm_extraction.py     # Metadata extraction
│   │   ├── schema.py             # Pydantic schemas
│   │   └── build_payloads.py     # Payload orchestration
│   ├── server/                    # MCP server
│   │   ├── mcp_server.py         # Main server
│   │   ├── handlers.py           # Tool handlers
│   │   ├── query_processor.py    # Result formatting
│   │   ├── config.py             # Server config
│   │   └── __main__.py           # Module entry point
│   └── utils/                     # Shared utilities
│       ├── citations.py          # Citation formatting
│       ├── config.py             # Config management
│       └── monitoring.py         # Performance monitoring
├── tests/                         # Test suite
├── pyproject.toml                # Package configuration
└── README.md                     # This file
```

## Data Flow

### 1. **Hierarchical Document Processing**:
   - Fetch documents from government APIs (CourtListener, Federal Register)
   - **Intelligent Chunking**:
     - **SCOTUS Opinions**: Break down by opinion type (syllabus, majority, concurring, dissenting), legal sections (I, II, III) and subsections (A, B, C), justice attribution
     - **Executive Orders**: Break down by header, sections (Sec. 1, Sec. 2), subsections, and signature blocks
   - **Rich Metadata Extraction**: Use GPT-5-nano to extract:
     - Legal/policy topics and key questions
     - Constitutional provisions and statutes cited
     - Court holdings and policy summaries
   - Generate embeddings for each chunk (SCOTUS: 600/800 tokens, EO: 300/400 tokens)
   - Store chunk embeddings + metadata in Qdrant

### 2. **Semantic Search & Retrieval**:
   - Convert user query to embedding
   - Search Qdrant for semantically similar **chunks**
   - Retrieve chunk metadata with opinion type, justice, section info
   - Return contextually relevant legal content to LLM

### 3. **Chunk-Aware Query Results**:
   - Users can search specifically within syllabus, majority, or dissenting opinions
   - Results include precise section references and justice attribution
   - Legal metadata enables topic-specific and citation-based searches

## Recent Updates

### Version 0.1.0 - Major Restructure (September 2025)

The codebase underwent a comprehensive restructure for improved maintainability and user experience:

**New CLI Framework:**
- Unified `governmentreporter` command with Click-based CLI
- Subcommands: `server`, `ingest scotus`, `ingest eo`, `query`
- Shell completion support for bash/zsh/fish
- Improved help documentation and option validation

**Modular Architecture:**
- New `cli/` module with dedicated command handlers
- New `ingestion/` module with base class pattern (eliminates ~500 lines of code duplication)
- Chunking split into organized submodules: `base.py`, `scotus.py`, `executive_orders.py`
- Better separation of concerns across all modules

**Developer Experience:**
- All scripts migrated to proper CLI commands
- Backwards-compatible imports through `__init__.py` exports
- Comprehensive docstrings and type hints
- Modern `src/` layout for Python packaging best practices

**Key Benefits:**
- Single entry point (`governmentreporter`) for all operations
- Consistent command structure across all features
- Easy to extend with new document types or commands
- Better error handling and user feedback

## Prerequisites

- Python 3.11+
- uv package manager
- OpenAI API key
- CourtListener API token (free registration required)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/governmentreporter.git
   cd governmentreporter
   ```

2. **Install uv package manager** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install Python dependencies**
   ```bash
   uv sync
   ```

4. **Setup API keys**
   ```bash
   # Create .env file with required API keys
   cat > .env << EOF
   OPENAI_API_KEY="your-openai-api-key-here"
   COURT_LISTENER_API_TOKEN="your-courtlistener-token-here"
   EOF
   ```

   **Get API Keys:**
   - **OpenAI API**: Get key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **CourtListener API**: Free registration at [CourtListener](https://www.courtlistener.com/api/)

## Usage

GovernmentReporter provides a unified CLI command `governmentreporter` with several subcommands:

### Start the MCP Server
```bash
# Using the CLI (recommended)
uv run governmentreporter server

# Or using Python module
uv run python -m governmentreporter.server
```

### Ingest Documents
```bash
# Ingest Supreme Court opinions for a date range
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31

# Ingest Executive Orders for a date range
uv run governmentreporter ingest eo --start-date 2024-01-01 --end-date 2024-12-31

# Customize batch size and database paths
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --batch-size 100 \
  --progress-db ./data/progress/scotus.db \
  --qdrant-db-path ./data/qdrant/qdrant_db
```

### View Database Information
```bash
# List all collections and their statistics
uv run governmentreporter info collections

# View sample documents from a collection
uv run governmentreporter info sample scotus
uv run governmentreporter info sample eo --limit 10 --show-text

# View detailed statistics for a collection
uv run governmentreporter info stats scotus
uv run governmentreporter info stats eo
```

### Test Semantic Search
```bash
# Search across all document types
uv run governmentreporter query "environmental regulation Commerce Clause"

# The query command tests the vector database and displays results
```

### Shell Completion
```bash
# Install shell completion for bash/zsh/fish
uv run governmentreporter --install-completion

# Show completion code
uv run governmentreporter --show-completion
```

### Server Configuration
Optional environment variables for the MCP server:
```bash
# Server settings
MCP_SERVER_NAME="Custom MCP Server"
MCP_LOG_LEVEL=DEBUG
MCP_DEFAULT_SEARCH_LIMIT=15
MCP_MAX_SEARCH_LIMIT=50

# Qdrant settings (if not using defaults)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-key-here

# Caching
MCP_ENABLE_CACHE=true
```

### MCP Server Status: ✅ Fully Functional

The GovernmentReporter MCP server is **production-ready** and fully compliant with the MCP specification. All required components are implemented and tested:

- ✅ stdio transport (JSON-RPC 2.0)
- ✅ Server lifecycle management (initialize, start, shutdown)
- ✅ 5 semantic search tools for government documents
- ✅ 2 resource types for full document access
- ✅ Qdrant vector database integration
- ✅ Query result formatting optimized for LLM consumption
- ✅ Polymorphic API client architecture for document retrieval
- ✅ Environment variable configuration
- ✅ Error handling and logging

### MCP Tools Available to LLMs

1. **`search_government_documents`** - Cross-collection semantic search
   - Search across SCOTUS opinions and Executive Orders
   - Configurable limits and document type filtering

2. **`search_scotus_opinions`** - SCOTUS-specific search with advanced filters
   - Filter by opinion type (majority, concurring, dissenting, syllabus)
   - Filter by authoring justice and date range
   - Rich legal metadata in results

3. **`search_executive_orders`** - Executive Order search with policy filters
   - Filter by president, agencies, and policy topics
   - Date range filtering
   - Policy context and agency impacts in results

4. **`get_document_by_id`** - Document retrieval by ID
   - Retrieve specific chunks by ID
   - Optional full document retrieval from government APIs

5. **`list_collections`** - Collection information
   - List all available collections with statistics
   - Metadata field descriptions

### MCP Resources Available to LLMs

Resources provide direct access to full government documents, complementing the search tools with complete document content fetched on-demand from government APIs.

1. **`scotus://opinion/{opinion_id}`** - Supreme Court Opinion
   - Full text of a Supreme Court opinion by opinion ID
   - Fetched in real-time from CourtListener API
   - Includes complete opinion text with all sections
   - Example: `scotus://opinion/12345678`

2. **`eo://document/{document_number}`** - Executive Order
   - Full text of a Presidential Executive Order
   - Fetched in real-time from Federal Register API
   - Includes complete order text with all sections
   - Example: `eo://document/2024-12345`

**Resource Features:**
- **Polymorphic Design**: Uses abstract base class interface for consistent document fetching
- **Fresh Data**: Always retrieves current version from government APIs
- **No Storage Overhead**: Documents fetched on-demand, not stored locally
- **Future-Proof**: Easy to add new document types (Congress bills, Federal Register notices, etc.)

## Claude Desktop Integration Tutorial

This tutorial walks you through connecting the GovernmentReporter MCP server to Claude Desktop, enabling Claude to search government documents and provide legal research assistance.

### Prerequisites

Before starting, ensure you have:
- ✅ Python 3.11+ and `uv` package manager installed
- ✅ Qdrant running locally (default: `localhost:6333`) or configured for remote/cloud
- ✅ Government documents indexed in Qdrant collections (see "Ingest Documents" section)
- ✅ Claude Desktop app installed
- ✅ Required API keys in `.env` file (OpenAI API key required)

### Step 1: Configure Claude Desktop for MCP

Claude Desktop uses a configuration file to connect to MCP servers. The location depends on your operating system:

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Create MCP Configuration

Create or edit the `claude_desktop_config.json` file with the following configuration:

```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": [
        "run",
        "governmentreporter",
        "server"
      ],
      "cwd": "/path/to/your/governmentreporter",
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "COURT_LISTENER_API_TOKEN": "your-courtlistener-token-here"
      }
    }
  }
}
```

**Important:** Replace `/path/to/your/governmentreporter` with the actual path to your project directory.

### Step 3: Alternative Configuration Methods

#### Option A: Using Environment Variables (Recommended)
If you already have a `.env` file in your project:

```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": [
        "run",
        "governmentreporter",
        "server"
      ],
      "cwd": "/path/to/your/governmentreporter"
    }
  }
}
```

#### Option B: Using Python Module
If you prefer running the Python module directly:

```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "governmentreporter.server"
      ],
      "cwd": "/path/to/your/governmentreporter",
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "COURT_LISTENER_API_TOKEN": "your-courtlistener-token-here"
      }
    }
  }
}
```

### Step 4: Verify Qdrant is Running

Ensure your local Qdrant instance is running and accessible:

```bash
# Check if Qdrant is responding
curl http://localhost:6333/health

# Expected response: {"status":"ok"}
```

If Qdrant isn't running, start it:

```bash
# Using Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant

# Or using local installation
qdrant --config-path ./qdrant-config.yaml
```

### Step 5: Restart Claude Desktop

After saving the configuration file:

1. **Completely quit** Claude Desktop (Cmd+Q on macOS, or close from system tray)
2. **Restart** Claude Desktop
3. Wait for the app to fully load

### Step 6: Test Server Locally (Optional)

Before testing with Claude Desktop, you can verify the server works:

```bash
# Test server startup (will run until interrupted with Ctrl+C)
uv run governmentreporter server

# Or with debug logging
uv run governmentreporter server --log-level DEBUG
```

You should see:
```
INFO - Initializing GovernmentReporter MCP Server...
INFO - Connected to Qdrant. Available collections: [...]
INFO - MCP server initialized successfully
INFO - Starting GovernmentReporter MCP Server...
```

Press Ctrl+C to stop the test. Claude Desktop will start/stop the server automatically.

### Step 7: Verify Claude Desktop Connection

In a new Claude conversation, you should see:
- 🔧 A tools indicator in the interface
- The GovernmentReporter tools available when Claude needs to search legal documents

To test the connection, ask Claude:
> "What tools do you have access to?"

Claude should mention the 5 government document search tools.

### Step 8: Using the MCP Server

Now you can ask Claude legal research questions that will trigger the MCP tools and resources:

#### Example Tool Queries (Semantic Search):

**Supreme Court Research:**
```
"Find recent Supreme Court cases about environmental regulation and the Commerce Clause"
```

**Executive Order Analysis:**
```
"Search for Executive Orders signed by Biden related to climate policy"
```

**Specific Legal Questions:**
```
"What did the Supreme Court say about the major questions doctrine in recent cases?"
```

**Cross-Document Research:**
```
"Find cases and executive orders related to cryptocurrency regulation"
```

#### Example Resource Queries (Full Document Access):

**Get Full Supreme Court Opinion:**
```
User: "Find cases about CFPB"
Claude: [Uses search tool, finds opinion ID 12345678]

User: "Show me the full text of that opinion"
Claude: [Uses resource scotus://opinion/12345678 to fetch complete opinion]
```

**Get Full Executive Order:**
```
User: "Find executive orders about cryptocurrency"
Claude: [Uses search tool, finds document number 2024-12345]

User: "Read the full executive order text"
Claude: [Uses resource eo://document/2024-12345 to fetch complete order]
```

**Workflow Combining Search and Resources:**
```
User: "What did Justice Alito say in the CFPB case, and show me the full opinion"

Claude workflow:
1. Uses search_scotus_opinions tool with query "CFPB" and justice filter "Alito"
2. Finds relevant chunks from dissenting opinion
3. Uses scotus://opinion/{id} resource to fetch full opinion text
4. Analyzes and quotes specific passages from Justice Alito's dissent
```

### Step 9: Understanding Claude's Responses

When Claude uses the MCP server, you'll see:

1. **Tool Usage Indicator** - Claude will show when it's searching documents or accessing resources
2. **Structured Results** - Claude will present findings with:
   - Case names and citations
   - Opinion types (majority, dissenting, etc.)
   - Executive Order numbers and dates
   - Relevant legal metadata
   - Direct quotes from documents
   - Relevance scores
3. **Resource Access** - When Claude fetches full documents via resources:
   - Complete opinion or order text
   - All sections and subsections
   - Full metadata
   - Fresh data from government APIs
4. **Source Attribution** - Claude will reference specific documents and provide context

The MCP server returns results formatted specifically for LLM consumption, with hierarchical document structure (sections, opinion types) and rich legal/policy metadata. Resources provide complete documents when chunks aren't sufficient.

### Advanced Configuration

#### Custom Server Settings
You can customize the MCP server behavior with environment variables:

```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": ["run", "governmentreporter", "server"],
      "cwd": "/path/to/your/governmentreporter",
      "env": {
        "OPENAI_API_KEY": "your-key-here",
        "COURT_LISTENER_API_TOKEN": "your-token-here",
        "MCP_SERVER_NAME": "My Legal Research Assistant",
        "MCP_DEFAULT_SEARCH_LIMIT": "15",
        "MCP_LOG_LEVEL": "INFO",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333"
      }
    }
  }
}
```

#### Multiple Collection Support
If you have additional document collections:

```json
{
  "env": {
    "MCP_COLLECTIONS": "supreme_court_opinions,executive_orders,federal_register"
  }
}
```

### Troubleshooting

#### Common Issues:

**1. Claude doesn't show any tools:**
- Check that `claude_desktop_config.json` is in the correct location
- Verify JSON syntax is valid (use a JSON validator)
- Restart Claude Desktop completely

**2. "Server failed to start" errors:**
- Verify the `cwd` path points to your project directory
- Check that `uv` is installed and accessible
- Ensure your `.env` file contains required API keys

**3. "Connection refused" errors:**
- Confirm Qdrant is running on `localhost:6333`
- Check firewall settings
- Verify Qdrant health endpoint: `curl http://localhost:6333/health`

**4. Empty search results:**
- Ensure your Qdrant database contains indexed documents
- Check collection names match your configuration
- Verify documents were properly ingested

#### Debug Mode:
Enable detailed logging by setting:
```json
{
  "env": {
    "MCP_LOG_LEVEL": "DEBUG"
  }
}
```

Check Claude Desktop logs (usually in Console.app on macOS) for detailed error messages.

### Security Considerations

- **API Keys**: Never commit API keys to version control
- **Local Access**: The MCP server runs locally and only responds to Claude Desktop
- **Network**: Ensure Qdrant is not exposed to external networks unless needed
- **Logs**: Monitor logs for any sensitive information exposure

### Next Steps

Once connected, you can:
- Ask Claude complex legal research questions
- Request analysis across multiple document types
- Get summaries of legal trends and developments
- Find specific citations and legal precedents
- Analyze policy impacts and agency relationships

The MCP integration enables Claude to become a powerful legal research assistant with access to your curated government document database.

## Data Processing Pipeline

The system follows a structured processing pipeline powered by the processors module:

1. **Document Fetching** (APIs Module):
   - SCOTUS: CourtListener API for opinion and cluster data
   - Executive Orders: Federal Register API for order data and raw text

2. **Hierarchical Chunking** (Processors Module - `chunking.py`):
   - SCOTUS: Split by opinion type → sections → paragraphs (600/800 tokens)
   - Executive Orders: Split by header → sections → subsections → tail (300/400 tokens)

3. **Metadata Extraction** (Processors Module - `llm_extraction.py`):
   - Use GPT-5-nano to extract rich legal/policy metadata
   - Generate bluebook citations and structured metadata
   - Validate with Pydantic schemas (`schema.py`)

4. **Payload Building** (Processors Module - `build_payloads.py`):
   - Orchestrates chunking and metadata extraction
   - Creates Qdrant-ready payloads with standardized structure

5. **Embedding Generation** (Processors Module - `embeddings.py`):
   - OpenAI text-embedding-3-small for semantic embeddings
   - Batch processing for efficiency with retry logic
   - Each chunk gets its own 1536-dimensional embedding vector

6. **Storage** (Database Module - `ingestion.py`):
   - Batch ingestion with progress tracking via `QdrantIngestionClient`
   - Duplicate detection and deterministic chunk IDs
   - Performance monitoring with `PerformanceMonitor` from utils

7. **Search & Retrieval**:
   - User query converted to embedding
   - Qdrant returns similar chunk metadata
   - Fresh content can be retrieved on-demand from government APIs

### Example Query Flows

#### SCOTUS Legal Research
```
User: "Find recent Supreme Court decisions about environmental regulation"

1. Query embedded and searched in Qdrant across SCOTUS chunks
2. Matching chunks returned with metadata:
   - Case names, citations, dates
   - Opinion type (syllabus, majority, concurring, dissenting)
   - Justice attribution and section references
   - Legal topics: ["Environmental Law", "Administrative Law", "Commerce Clause"]
3. Contextually relevant Supreme Court content provided to LLM
```

#### Executive Order Policy Research
```
User: "Find Executive Orders about aviation regulatory reform"

1. Query searches Executive Order chunks in Qdrant
2. Matching chunks returned with metadata:
   - EO numbers, titles, signing dates, presidents
   - Policy topics: ["aviation", "regulatory reform", "transportation"]
   - Impacted agencies: ["FAA", "DOT"]
   - Section and subsection references
3. Relevant policy content provided to LLM
```

#### Cross-Document Legal Analysis
```
User: "Find cases and executive orders about financial regulation"

1. Query searches across both SCOTUS and EO collections
2. Returns mixed results with:
   - SCOTUS: Court interpretations and legal precedents
   - Executive Orders: Policy directives and regulatory changes
   - Related agencies, statutes, and constitutional provisions
3. Comprehensive legal and policy analysis across document types
```

## Hierarchical Chunking System

### Supreme Court Opinion Structure

GovernmentReporter automatically identifies and chunks Supreme Court opinions using sophisticated pattern recognition:

#### Opinion Types Detected:
- **Syllabus**: Court's official summary (usually 1-2 chunks)
- **Majority Opinion**: Main opinion of the court (10-25 chunks depending on length)
- **Concurring Opinions**: Justices agreeing with result but with different reasoning
- **Dissenting Opinions**: Justices disagreeing with the majority

#### Section Detection:
- **Major Sections**: Roman numerals (I, II, III, IV)
- **Subsections**: Capital letters (A, B, C, D)
- **Smart Chunking**: Target 600 tokens, max 800 tokens while preserving paragraph boundaries

#### SCOTUS Metadata Per Chunk:
```json
{
  "text": "The actual chunk content...",
  "opinion_type": "majority",
  "justice": "Thomas",
  "section": "II.A",
  "chunk_index": 3,
  "case_name": "Consumer Financial Protection Bureau v. Community Financial Services Assn.",
  "citation": "601 U.S. 416 (2024)",
  "legal_topics": ["Constitutional Law", "Administrative Law", "Appropriations Clause"],
  "constitutional_provisions": ["Art. I, § 9, cl. 7"],
  "statutes_interpreted": ["12 U.S.C. § 5497(a)(1)"],
  "holding": "Congress' statutory authorization satisfies the Appropriations Clause",
  "vote_breakdown": "7-2"
}
```

### Executive Order Structure

#### Document Parts Detected:
- **Header**: Title, authority, preamble ("it is hereby ordered")
- **Sections**: Numbered sections (Sec. 1, Sec. 2, etc.) with titles
- **Subsections**: Lettered subsections (a), (b), (c) and numbered items (1), (2)
- **Tail**: Signature block, filing information

#### EO Processing Features:
- **Smart Chunking**: Target 300 tokens, max 400 tokens with overlap between chunks
- **Section Titles**: Preserved (e.g., "Sec. 2. Regulatory Reform for Supersonic Flight")
- **HTML Cleaning**: Removes markup from Federal Register raw text

#### Executive Order Metadata Per Chunk:
```json
{
  "text": "The actual chunk content...",
  "chunk_type": "section",
  "section_title": "Sec. 2. Regulatory Reform for Supersonic Flight",
  "subsection": "(a)",
  "chunk_index": 4,
  "document_number": "2024-05678",
  "title": "Promoting Access to Voting",
  "executive_order_number": "14117",
  "president": "Biden",
  "signing_date": "2024-03-07",
  "summary": "Enhances federal efforts to promote access to voting...",
  "policy_topics": ["voting rights", "civil rights", "federal agencies"],
  "impacted_agencies": ["DOJ", "DHS", "VA"],
  "legal_authorities": ["52 U.S.C. § 20101"],
  "economic_sectors": ["government", "civic participation"]
}
```

### Processing Pipeline

**Supreme Court Opinions:**
1. **CLI Command** (`cli/ingest.py`): Entry point for ingestion commands
2. **Pipeline Orchestration** (`ingestion/scotus.py`): Coordinates the full ingestion process
3. **API Retrieval** (`apis/court_listener.py`): Fetch opinion and cluster data from CourtListener
4. **Opinion Type Detection** (`processors/chunking/scotus.py`): Use regex patterns to identify different opinion types
5. **Section Parsing** (`processors/chunking/scotus.py`): Detect Roman numeral sections and lettered subsections
6. **Intelligent Chunking** (`processors/chunking/base.py`, `scotus.py`): Target 600 tokens, max 800 tokens while preserving legal structure
7. **Metadata Extraction** (`processors/llm_extraction.py`): Use GPT-5-nano for rich legal metadata
8. **Citation Formatting** (`utils/citations.py`): Build proper bluebook citations from cluster data
9. **Payload Building** (`processors/build_payloads.py`): Orchestrate processing and create Qdrant-ready payloads
10. **Embedding Generation** (`processors/embeddings.py`): Create semantic embeddings for each chunk
11. **Progress Tracking** (`ingestion/progress.py`): Track processing state and enable resumption
12. **Database Storage** (`database/ingestion.py`, `qdrant.py`): Batch store chunks with complete metadata in Qdrant

**Executive Orders:**
1. **CLI Command** (`cli/ingest.py`): Entry point for ingestion commands
2. **Pipeline Orchestration** (`ingestion/executive_orders.py`): Coordinates the full ingestion process
3. **API Retrieval** (`apis/federal_register.py`): Fetch order data and raw text from Federal Register
4. **Structure Detection** (`processors/chunking/executive_orders.py`): Identify header, sections, subsections, and tail blocks
5. **HTML Cleaning** (`apis/federal_register.py`): Remove markup and extract clean text
6. **Intelligent Chunking** (`processors/chunking/base.py`, `executive_orders.py`): Target 300 tokens, max 400 tokens with sentence overlap
7. **Metadata Extraction** (`processors/llm_extraction.py`): Use GPT-5-nano for policy metadata
8. **Schema Validation** (`processors/schema.py`): Validate metadata with Pydantic models
9. **Payload Building** (`processors/build_payloads.py`): Orchestrate processing and create Qdrant-ready payloads
10. **Embedding Generation** (`processors/embeddings.py`): Create semantic embeddings for each chunk
11. **Progress Tracking** (`ingestion/progress.py`): Track processing state and enable resumption
12. **Database Storage** (`database/ingestion.py`, `qdrant.py`): Batch store chunks with complete metadata in Qdrant

## Government Data Sources

### Supreme Court Opinions
- **Source**: CourtListener API (Free Law Project)
- **Coverage**: Comprehensive collection of SCOTUS opinions from 1900+
- **API**: `https://www.courtlistener.com/api/rest/v4/`
- **Rate Limit**: 0.1 second delay between requests
- **Authentication**: Free API token required

### Executive Orders
- **Source**: Federal Register API
- **Coverage**: All presidential Executive Orders by date range
- **API**: `https://www.federalregister.gov/api/v1/`
- **Rate Limit**: 1.1 second delay (60 requests/minute limit)
- **Authentication**: No API key required
