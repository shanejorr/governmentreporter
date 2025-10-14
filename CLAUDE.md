# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovernmentReporter is an MCP (Model Context Protocol) server that provides LLMs with access to US federal government publications through RAG. The system uses **hierarchical document chunking** to intelligently break down Supreme Court opinions and Executive Orders by their natural structure (opinion types/sections/subsections), stores semantic embeddings and rich metadata in Qdrant, and retrieves fresh document text on-demand from government APIs.

**Key Documentation:**
- `README.md` - Comprehensive project documentation, features, architecture, and Claude Desktop integration tutorial
- `QUICK_START.md` - Get started in 5 minutes with Docker or local development
- `DEPLOYMENT.md` - Production deployment guide for Docker, cloud platforms (AWS/GCP/Azure), and systemd
- `.env.example` - Complete environment variable reference with descriptions


## Development Commands

### Package Management
- `uv sync` - Install dependencies
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run commands in virtual environment

### Code Quality & Testing
- `uv run black .` - Format code (Python Black formatter)
- `uv run isort .` - Sort imports (automatically organizes import statements)
- `uv run mypy src/` - Type checking (static type analysis)
- `uv run pytest tests/` - Run full test suite
- `uv run pytest tests/ -v` - Run tests with verbose output
- `uv run pytest tests/ -v --tb=short` - Run tests with short traceback
- `uv run pytest tests/test_file.py::test_function` - Run single test function
- `uv run pytest tests/test_processors/` - Run tests for specific module
- `uv run pytest tests/ --cov=src/governmentreporter` - Run tests with coverage report

### Running the Application

#### Server Commands
- `uv run governmentreporter server` - Start MCP server (stdio transport for Claude Desktop)
- `uv run python -m governmentreporter.server` - Alternative: Start server via Python module

#### Ingestion Commands
- `uv run governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Ingest SCOTUS opinions
- `uv run governmentreporter ingest eo --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Ingest Executive Orders
- `uv run governmentreporter ingest all --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Ingest both sequentially (recommended)
- `caffeinate -i uv run governmentreporter ingest all --start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Keep macOS awake during long ingestion
- `uv run governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD --batch-size 100` - Custom batch size for faster ingestion
- `uv run governmentreporter ingest all --start-date YYYY-MM-DD --end-date YYYY-MM-DD --dry-run` - Test ingestion without storing

#### Delete Commands
- `uv run governmentreporter delete --all` - Delete all Qdrant collections (with confirmation prompt)
- `uv run governmentreporter delete --scotus` - Delete SCOTUS collection + progress database
- `uv run governmentreporter delete --eo` - Delete Executive Orders collection + progress database
- `uv run governmentreporter delete --scotus --eo` - Delete multiple collections at once
- `uv run governmentreporter delete --collection <name>` - Delete specific collection by name
- `uv run governmentreporter delete --all -y` - Delete all collections without confirmation (⚠️ dangerous!)

#### Info Commands
- `uv run governmentreporter info collections` - List all collections with statistics
- `uv run governmentreporter info sample scotus` - View sample SCOTUS documents
- `uv run governmentreporter info sample eo --limit 10 --show-text` - View sample EO documents with full text
- `uv run governmentreporter info stats scotus` - Show detailed statistics for SCOTUS collection
- `uv run governmentreporter info stats eo` - Show detailed statistics for EO collection

#### Query Commands
- `uv run governmentreporter query "search text"` - Test semantic search across all collections

#### Shell Completion
- `uv run governmentreporter --install-completion` - Install shell completion (bash/zsh/fish)
- `uv run governmentreporter --show-completion` - Display shell completion code
- `uv run governmentreporter --help` - Show all available commands

**Important Notes:**
- The `delete` command removes BOTH the Qdrant collection AND its ingestion progress database (`./data/progress/`)
- Ingestion is resumable - if interrupted, re-run the same command to resume from where it stopped
- Progress tracking databases allow duplicate detection and resumption after failures

## Architecture

### Core Components

**CLI Module** (`src/governmentreporter/cli/`)
- `main.py` - Primary CLI entry point using Click framework, shell completion support
- `ingest.py` - Ingestion commands for SCOTUS, Executive Orders, and combined ingestion
- `delete.py` - Collection deletion commands with confirmation prompts
- `info.py` - Database inspection commands (collections, samples, statistics)
- `query.py` - Test semantic search functionality
- `server.py` - MCP server start command

**APIs Module** (`src/governmentreporter/apis/`)
- `base.py` - Abstract base classes for API clients with polymorphic design
- `court_listener.py` - CourtListener API v4 client for SCOTUS opinions and clusters
- `federal_register.py` - Federal Register API client for Executive Orders and raw text retrieval

**Database Module** (`src/governmentreporter/database/`)
- `qdrant.py` - Core Qdrant client with collection management and search operations
- `ingestion.py` - High-performance batch ingestion with duplicate detection and progress monitoring

**Ingestion Module** (`src/governmentreporter/ingestion/`)
- `base.py` - Abstract base class for ingestion pipelines (eliminates ~500 lines of code duplication)
- `scotus.py` - Supreme Court opinion ingestion pipeline with cluster-based fetching
- `executive_orders.py` - Executive Order ingestion pipeline with HTML cleaning
- `progress.py` - SQLite-based progress tracking for resumable operations

**Processors Module** (`src/governmentreporter/processors/`)
- `chunking/` - Hierarchical document chunking algorithms
  - `base.py` - Core chunking utilities and sliding window algorithm
  - `scotus.py` - SCOTUS-specific chunking (opinion types, sections, subsections, justice attribution)
  - `executive_orders.py` - EO-specific chunking (header, sections, subsections, tail, no cross-section overlap)
- `embeddings.py` - OpenAI text-embedding-3-small integration with batch processing and retry logic
- `llm_extraction.py` - GPT-5-mini metadata extraction (summaries, validated citations, topics)
- `schema.py` - Pydantic data validation models for type safety
- `build_payloads.py` - Orchestrates chunking and metadata extraction into Qdrant-ready payloads

**Server Module** (`src/governmentreporter/server/`)
- `mcp_server.py` - Main MCP server with tool registration and lifecycle management
- `handlers.py` - Tool handlers for search, retrieval, and collection operations (5 tools)
- `resources.py` - Resource handlers for full document access (SCOTUS opinions, Executive Orders)
- `query_processor.py` - Result formatting optimized for LLM consumption
- `config.py` - Server configuration with environment variable support
- `__main__.py` - Module entry point for `python -m governmentreporter.server`

**Utils Module** (`src/governmentreporter/utils/`)
- `citations.py` - Bluebook citation formatting for legal references
- `config.py` - Environment variable and credential management
- `monitoring.py` - Performance monitoring with progress tracking and logging

### Data Flow

**Indexing Pipeline:**
1. **Fetch Documents** - CourtListener API (SCOTUS) or Federal Register API (Executive Orders)
2. **Hierarchical Chunking** - Opinion types/sections for SCOTUS; header/sections/subsections for EOs
3. **Document-Level Metadata Extraction** - GPT-5-mini extracts technical summaries, validated citations, topics
4. **Generate Embeddings** - OpenAI text-embedding-3-small (1536-dimensional vectors)
5. **Store in Qdrant** - Batch ingestion with duplicate detection and progress tracking

**Querying Pipeline:**
1. **Embed Query** - Convert user query to embedding vector
2. **Semantic Search** - Qdrant vector similarity search across indexed chunks
3. **Return Results** - Chunks with rich metadata (opinion type, section, justice, topics, citations)
4. **Optional Full-Text Retrieval** - MCP resources fetch fresh full documents from government APIs on-demand

### External Dependencies

**Vector Database:**
- **Qdrant** (localhost:6333 by default) - Stores embeddings, metadata, and supports semantic search
- Docker image: `qdrant/qdrant:latest`

**AI Services:**
- **OpenAI API** (api.openai.com)
  - `gpt-5-mini` - Document-level metadata extraction (summaries, validated citations, topics)
  - `text-embedding-3-small` - 1536-dimensional semantic embeddings

**Government APIs:**
- **CourtListener API v4** (www.courtlistener.com) - SCOTUS opinions, clusters, and metadata (requires free API token)
- **Federal Register API** (www.federalregister.gov) - Executive Orders and raw text (no API key required)

### Project Structure

The project follows a modular `src/` layout with main source code in `src/governmentreporter/` organized into 7 core modules (apis, cli, database, ingestion, processors, server, utils). Tests mirror the source structure in `tests/`. Runtime data (Qdrant database, progress tracking, logs) is stored in `data/` (git-ignored). Configuration files include `.env` (git-ignored, create from `.env.example`), `pyproject.toml`, `docker-compose.yml`, and `logging.yaml`. See README.md, QUICK_START.md, and DEPLOYMENT.md for comprehensive documentation.

### Example API Response Formats

Reference files in `scratch/` directory show actual API response structures:

**CourtListener API (SCOTUS):**
- API Documentation: `scratch/courtlistener_caselaw_api.md` - CourtListener API documentation for fetching US Supreme Court decisions
- Clusters Endpoint: `scratch/courtlistener_clusters_endpoint.json` - Case metadata, citations, vote counts
- Opinions Endpoint: `scratch/courtlistener_opinion_endpoint.json` - Opinion metadata
- Opinion Plain Text: `scratch/courtlistener_opinion_html_text.json` - Full opinion text from 'html_with_citations' field, which is the field used to retrieve the opinion text.

**Federal Register API (Executive Orders):**
- Metadata: `scratch/executive_order_metadata.json` - EO number, title, president, signing date, agencies
- Raw Text: `scratch/executive_order_text.txt` - Full order text from "raw_text_url" field (HTML format)

## Key Implementation Notes

### Development Philosophy
- **Be Honest, Not Agreeable**: I am an intermediate Python programmer. If I ask you to do something that isn't the best approach, please say so. If I ask a question, answer truthfully. Do not simply agree with me.
- **Breaking Changes Are OK**: The application has not been deployed to production. It is acceptable to make breaking changes for architectural improvements.
- **Code Quality First**: Prioritize clean, maintainable code over quick hacks. Use type hints, comprehensive docstrings, and clear variable names.

### Documentation Standards
- **Extensive Docstrings**: Include robust docstrings for all classes and methods
- **Beginner-Friendly Explanations**: Documentation should explain code to a beginner Python programmer
- **Tutorial-Style Comments**: Documentation should serve as a Python learning resource, explaining WHY code works the way it does, not just WHAT it does
- **Type Hints**: Use Pydantic models and Python type hints for all function signatures

### Code Organization
- **Modular Architecture**: New ingestion module with base class eliminates ~500 lines of code duplication
- **Separation of Concerns**: CLI, APIs, Database, Ingestion, Processors, Server, and Utils modules are cleanly separated
- **Abstract Base Classes**: Use polymorphic design (e.g., `BaseAPIClient`, `BaseIngester`) for extensibility
- **Single Entry Point**: Unified `governmentreporter` CLI command using Click framework

### MCP Server Implementation
- **Fully Production-Ready**: MCP server is complete and compliant with Model Context Protocol specification
- **5 Search Tools**: Cross-collection search, SCOTUS-specific, Executive Order-specific, document retrieval, collection listing
- **2 Resource Types**: Full document access via `scotus://opinion/{id}` and `eo://document/{number}`
- **stdio Transport**: JSON-RPC 2.0 communication for Claude Desktop integration
- **Real-Time API Retrieval**: Resources fetch fresh document text on-demand from government APIs
- **Intelligent Full-Document Hints**: Query processor automatically generates context-aware hints in search results, guiding LLMs to proactively load complete documents when appropriate (≤3 results, score ≥0.4). Eliminates redundant tool calls for multi-turn conversations. Implementation: `query_processor.py::_generate_full_document_hint()` integrated into all format methods.

### Hierarchical Chunking System
- **SCOTUS Opinions**:
  - Detects opinion types (syllabus, majority, concurring, dissenting)
  - Identifies sections (I, II, III) and subsections (A, B, C)
  - Attributes chunks to specific justices for concurring/dissenting opinions
  - Target: 600 tokens, Max: 800 tokens, Overlap: 15% sliding window
- **Executive Orders**:
  - Separates header, sections (Sec. 1, Sec. 2), subsections, and tail
  - NO overlap across section boundaries (each section chunked independently)
  - Target: 340 tokens, Max: 400 tokens, Overlap: 10% within sections only

### Metadata Extraction
- **GPT-5-mini for Document-Level Context**: Generates technical summaries (1-2 dense sentences) optimized for LLM comprehension
- **Validated Citations Only**: Extracts text-backed citations (Constitution, statutes, regulations) - no hallucinations allowed
- **Topic Extraction**: Balances technical legal precision with searchability
- **Pydantic Validation**: All metadata validated with schemas before storage

### Progress Tracking & Resumability
- **SQLite Progress Databases**: Track ingestion status per document (pending, processing, completed, failed)
- **Duplicate Detection**: Deterministic chunk IDs prevent reprocessing
- **Resumable Operations**: Re-run ingestion commands to resume from failures
- **Progress Databases Location**: `./data/progress/scotus_ingestion.db` and `./data/progress/executive_orders_ingestion.db`

### Logging & Monitoring
- **Robust Logging**: All modules use Python logging with structured output
- **Configuration**: `logging.yaml` defines log levels, file handlers, and formats
- **Performance Monitoring**: `PerformanceMonitor` utility tracks processing times and throughput
- **Log Locations**: `./logs/` directory (ingestion.log, server.log, errors.log)

### Testing
- **Pytest Framework**: Comprehensive test suite in `tests/` directory
- **Test Coverage**: Tests for APIs, CLI, database, ingestion, processors, server, and utils
- **Fixtures**: `conftest.py` provides shared test fixtures
- **Mock API Responses**: Use `respx` for HTTP mocking in API tests

### Environment & Configuration
- **Environment Variables**: All configuration via `.env` file (see `.env.example` for template)
- **No Secrets in Git**: `.env` is git-ignored; use `.env.example` as template
- **Config Management**: `utils/config.py` handles environment variable loading with validation
- **Docker Support**: `docker-compose.yml` provides complete containerized environment

### Development Workflow
- **IDE**: VSCode (project is optimized for VS Code)
- **Package Manager**: uv (modern, fast Python package manager)
- **Version Control**: Git with `.gitignore` configured for Python/data/logs
- **Pre-commit Hooks**: `.pre-commit-config.yaml` runs Black, isort, and mypy
- **Python Version**: 3.11+ (tested on 3.11 and 3.12)

## Dependencies

All dependencies are managed in `pyproject.toml` with version pinning for reproducibility. Key runtime dependencies include: Click (CLI framework), Qdrant client (vector database), OpenAI API client (embeddings and LLM extraction), Pydantic (data validation), and MCP SDK (Model Context Protocol). Development dependencies include: Black, isort, mypy, pytest, and pytest plugins for testing/coverage. Use `uv sync` to install all dependencies.

## Quick Reference

**Essential Files:**
- `.env` (git-ignored) - Environment variables; create from `.env.example`
- `pyproject.toml` - Package configuration and dependencies
- `logging.yaml` - Logging configuration
- `data/` (git-ignored) - Qdrant database, progress tracking, logs
- `scratch/` - API response examples for reference

**Key Documentation:**
- `README.md` - Comprehensive project documentation
- `QUICK_START.md` - 5-minute quick start guide
- `DEPLOYMENT.md` - Production deployment guide
- `.env.example` - Environment variable template
