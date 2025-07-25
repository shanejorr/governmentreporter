# GovernmentReporter

An MCP (Model Context Protocol) server that provides LLMs with access to the latest US federal government publications through retrieval augmented generation (RAG).

## Overview

GovernmentReporter creates a ChromaDB vector database storing semantic embeddings and lightweight metadata for US federal Supreme Court opinions, Executive Orders, and federal legislation. Rather than storing full document text, the system uses on-demand API retrieval to access current documents from authoritative government sources. The database is wrapped in an MCP server, enabling LLMs to access fresh government publications through semantic search and real-time retrieval.

## Features

- **Comprehensive Government Data**: Indexes US Supreme Court opinions, Executive Orders, and federal legislation
- **Fresh Data Guarantee**: Retrieves latest document text on-demand from government APIs
- **Semantic Search**: Vector database enables intelligent document discovery using lightweight metadata
- **Cost-Effective Storage**: Stores only embeddings and metadata, not full text
- **MCP Integration**: Compatible with LLMs that support the Model Context Protocol
- **Local Processing**: Uses locally-run models for metadata generation

## Architecture

- **Language**: Python
- **Vector Database**: ChromaDB (embeddings + metadata only)
- **Local LLM**: deepseek-r1:8b (via Ollama) for metadata generation
- **Government APIs**: 
  - CourtListener API (Supreme Court opinions)
  - Federal Register API (Executive Orders)
  - Congress.gov API (Federal legislation)
- **Development**: VS Code with Claude Code support
- **Protocol**: Model Context Protocol (MCP)

## Data Flow

1. **Document Indexing**:
   - Fetch documents from government APIs
   - Generate embeddings from full document text
   - Create lightweight metadata with API identifiers and context identified by DeepSeek.
   - Store embeddings + metadata in ChromaDB

2. **Query Processing**:
   - Convert user query to embedding
   - Search ChromaDB for semantically similar documents
   - Retrieve metadata for top matches
   - Make API calls to fetch current full text
   - Return fresh document content to LLM

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed locally
- macOS (tested on Apple M2 Pro)
- 16GB+ RAM recommended
- Internet connection for API access

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/governmentreporter.git
   cd governmentreporter
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and setup Ollama**
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull the deepseek-r1 model
   ollama pull deepseek-r1:8b
   ```

4. **Configure the MCP server**
   ```bash
   # Copy example configuration
   cp config.example.json config.json
   
   # Edit configuration as needed
   nano config.json
   ```

## Usage

### Starting the MCP Server

```bash
python -m governmentreporter.server
```

### Data Pipeline

The system follows a three-step process:

1. **Initial Indexing**: 
   - Fetches documents from government APIs
   - Generates semantic embeddings from full text
   - Creates lightweight metadata using deepseek-r1:8b
   - Stores embeddings + metadata in ChromaDB

2. **Semantic Search**:
   - User query converted to embedding
   - ChromaDB returns similar document metadata
   - System identifies relevant government documents

3. **Real-time Retrieval**:
   - Makes API calls using stored identifiers
   - Fetches current document text from authoritative sources
   - Returns fresh content to LLM via MCP

### Example Query Flow

```
User: "Find recent Supreme Court decisions about environmental regulation"

1. Query embedded and searched in ChromaDB
2. Matching case metadata returned (case names, citations, dates, API endpoints)
3. Full text retrieved from CourtListener API for top matches
4. Current Supreme Court opinions provided to LLM
```

## Government Data Sources

### Supreme Court Opinions
- **Source**: CourtListener API (Free Law Project)
- **Coverage**: Comprehensive collection from multiple authoritative sources
- **API**: `https://www.courtlistener.com/api/rest/v4/`

### Executive Orders
- **Source**: Federal Register API
- **Coverage**: All presidential Executive Orders
- **API**: `https://www.federalregister.gov/api/v1/`

### Federal Legislation
- **Source**: Congress.gov API (Library of Congress)
- **Coverage**: Bills, resolutions, and legislative data
- **API**: `https://api.congress.gov/v3/`

## Configuration

Edit `config.json` to customize:

- Government API endpoints and rate limiting
- ChromaDB settings and collection parameters
- Ollama model configuration for metadata generation
- MCP server settings
- Document type priorities and filtering

## Running Tests

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Hardware Requirements

**Minimum Recommended:**
- Apple M2 Pro or equivalent
- 16GB RAM
- 10GB free storage (significantly reduced due to metadata-only approach)
- Stable internet connection for API access
- macOS 15.5+

## API Considerations

- **Rate Limits**: Government APIs have usage restrictions
- **Caching**: Frequently accessed documents are temporarily cached
- **Fallbacks**: Multiple data sources where available
- **Reliability**: Robust error handling and retry logic

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This project accesses public government documents through official APIs. Users must comply with:
- Government API terms of service
- Rate limiting requirements
- Appropriate use policies

The system retrieves current data from authoritative sources but users should verify critical information from primary government sources.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review government API documentation for data sources

---

**Note**: This project is designed for research and educational purposes. The metadata-only storage approach ensures access to the most current government publications while maintaining cost-effective operation.