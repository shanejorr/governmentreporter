# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovernmentReporter is an MCP (Model Context Protocol) server that provides LLMs with access to US federal government publications through RAG. The system stores semantic embeddings and metadata in Qdrant, then retrieves current document text on-demand from government APIs.

`scratch/program_structure.md` contains the project's structure, which uses the modern `src/` layout.
`README.md` contains more information about the project.


## Development Commands

### Package Management
- `uv sync` - Install dependencies
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run commands in virtual environment

### Code Quality
- `uv run black .` - Format code
- `uv run isort .` - Sort imports
- `uv run mypy src/` - Type checking
- `uv run pytest tests/` - Run tests
- `uv run pytest tests/test_file.py::test_function` - Run single test

### Running the Application
- `uv run governmentreporter server` - Start MCP server
- `uv run governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Ingest SCOTUS opinions
- `uv run governmentreporter ingest eo --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Ingest Executive Orders
- `uv run governmentreporter query "search text"` - Search documents (test semantic search)
- `uv run governmentreporter --install-completion` - Install shell completion (bash/zsh/fish)
- `uv run governmentreporter --help` - Show all available commands

## Architecture

### Core Components
- **CLI Module** (`src/governmentreporter/cli/`): Command-line interface for server and ingestion
- **APIs Module** (`src/governmentreporter/apis/`): Government API clients (CourtListener, Federal Register)
- **Database Module** (`src/governmentreporter/database/`): Qdrant integration for vector storage
- **Ingestion Module** (`src/governmentreporter/ingestion/`): Document ingestion pipelines with progress tracking
- **Processors Module** (`src/governmentreporter/processors/`): Document chunking, embeddings, metadata extraction
  - `chunking/`: Split into base utilities, SCOTUS-specific, and EO-specific chunking
- **Server Module** (`src/governmentreporter/server/`): MCP server implementation
- **Utils Module** (`src/governmentreporter/utils/`): Shared utilities and helpers

### Data Flow
1. **Indexing**: Fetch documents → Generate embeddings → Create metadata with GPT-5-nano → Store in Qdrant
2. **Querying**: Query embedding → Qdrant search → API retrieval → Return fresh content

### External Dependencies
- **Qdrant**: Vector database for embeddings and metadata storage
- **OpenAI API**: GPT-5-nano for metadata generation, text-embedding-3-small for embeddings
- **Government APIs**: CourtListener, Federal Register, Congress.gov for document retrieval

### Example API formatting
- **CourtListener (For court opinions)**:
  - Opinions Endpoint: `scratch/opinions_endpoint.json`
  - Opinions Cluster Endpoint: `scratch/cluster_endpoint.json`
- **Federal Register API (for federal executive orders)**:
  - Metadata: `scratch/executive_order_metadata.json`
  - Order Text (from "raw_text_url" key in `scratch/executive_order_metadata.json`): `scratch/executive_order_text.txt`

## Key Implementation Notes

- The codebase is in early development
- VSCode is the IDE used for development
- Ensure robust logging
- It is OK to make breaking changes. The application has not been deployed.
- MCP protocol integration for LLM compatibility
- Real-time document retrieval ensures fresh government data
- I am an intermediate Python programmer. If I ask you to do something and you do not think it is the best approach please say so. If I ask a question please answer truthfully. Do not simply agree with me.
- Extensively document the code. The documentation should say what the code does and how it works. Include robust docstrings to all classes and methods. The documentation should explain the code, classes, and methods to a beginner Python programmer. Documentation should also serve as a Python tutorial and help a beginner learn Python.

## Recent Restructure (2025)

The codebase was recently restructured for better organization and maintainability:

1. **Scripts → CLI + Ingestion Module**: Former `scripts/` directory migrated to proper modules
   - New `cli/` module with Click-based commands
   - New `ingestion/` module with base class pattern (eliminates ~500 lines of duplication)

2. **Chunking Split**: `chunking.py` (840 lines) split into organized submodule
   - `chunking/base.py` - Shared utilities and core algorithm
   - `chunking/scotus.py` - Supreme Court-specific chunking
   - `chunking/executive_orders.py` - Executive Order-specific chunking

3. **CLI Entry Points**: Added `governmentreporter` command with subcommands
   - `governmentreporter server` - Start MCP server
   - `governmentreporter ingest scotus` - Ingest Supreme Court opinions
   - `governmentreporter ingest eo` - Ingest Executive Orders

All imports remain backwards compatible through `__init__.py` exports.

## Dependencies

- Python 3.11+
- all dependencies are in `pyproject.toml`
