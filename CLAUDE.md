# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovernmentReporter is an MCP (Model Context Protocol) server that provides LLMs with access to US federal government publications through RAG. The system stores semantic embeddings and metadata in ChromaDB, then retrieves current document text on-demand from government APIs.

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
- `uv run python main.py` - Run main entry point
- `uv run python -m governmentreporter.server` - Start MCP server

## Architecture

### Core Components
- **APIs Module** (`src/governmentreporter/apis/`): Government API clients (CourtListener, Federal Register, Congress.gov)
- **Database Module** (`src/governmentreporter/database/`): ChromaDB integration for vector storage
- **Metadata Module** (`src/governmentreporter/metadata/`): Document metadata generation using Gemini 2.5 Flash-Lite API
- **Utils Module** (`src/governmentreporter/utils/`): Shared utilities and helpers

### Data Flow
1. **Indexing**: Fetch documents → Generate embeddings → Create metadata with Gemini 2.5 Flash-Lite → Store in ChromaDB
2. **Querying**: Query embedding → ChromaDB search → API retrieval → Return fresh content

### External Dependencies
- **ChromaDB**: Vector database for embeddings and metadata storage
- **Gemini 2.5 Flash-Lite API**: Google's API for metadata generation
- **Government APIs**: CourtListener, Federal Register, Congress.gov for document retrieval

## Key Implementation Notes

- The codebase is in early development - most modules contain only directory structure
- Uses metadata-only storage approach (embeddings + metadata, not full text)
- Designed for macOS with 16GB+ RAM
- MCP protocol integration for LLM compatibility
- Real-time document retrieval ensures fresh government data
- I am an intermediate Python programmer. If I ask you to do something and you do not think it is the best approach please say so. If I ask a question please answer truthfully. Do not simply agree with me.

## Dependencies

- Python 3.11+ (specified in pyproject.toml)
- Core: chromadb, mcp, ollama, httpx, requests, beautifulsoup4, feedparser
- Dev: black, isort, mypy, pytest