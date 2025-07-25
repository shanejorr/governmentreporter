# GovernmentReporter

An MCP (Model Context Protocol) server that provides LLMs with access to the latest US federal government publications through retrieval augmented generation (RAG).

## Overview

GovernmentReporter creates a ChromaDB vector database storing US federal Supreme Court opinions, Executive Orders, and federal legislation. The database is wrapped in an MCP server, enabling LLMs to access current government publications through semantic search and retrieval.

## Features

- **Comprehensive Government Data**: Stores US Supreme Court opinions, Executive Orders, and federal legislation
- **Real-time Access**: Pulls latest documents from government APIs
- **Semantic Search**: Vector database enables intelligent document retrieval
- **MCP Integration**: Compatible with LLMs that support the Model Context Protocol
- **Local Processing**: Uses locally-run models for metadata generation

## Architecture

- **Language**: Python
- **Vector Database**: ChromaDB
- **Local LLM**: deepseek-r1:8b (via Ollama)
- **Development**: VS Code with Claude Code support
- **Protocol**: Model Context Protocol (MCP)

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed locally
- macOS (tested on Apple M2 Pro)
- 16GB+ RAM recommended

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

1. **Data Ingestion**: Fetches documents from government APIs
   - Supreme Court opinions
   - Executive Orders
   - Federal legislation

2. **Vector Database Population**
   - Generates metadata using deepseek-r1:8b
   - Creates embeddings from document text
   - Stores vectors in ChromaDB

3. **MCP Server Deployment**
   - Serves the database through MCP protocol
   - Enables LLM access via semantic search

### Example Query

Once connected to an MCP-compatible LLM:

```
"Find recent Supreme Court decisions about environmental regulation"
```

## Configuration

Edit `config.json` to customize:

- API endpoints and keys
- ChromaDB settings
- Ollama model parameters
- MCP server configuration

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
- 50GB free storage
- macOS 15.5+

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This project accesses public government documents. Ensure compliance with relevant APIs' terms of service and usage guidelines.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review API documentation for data sources

---

**Note**: This project is designed for research and educational purposes. Always verify information from primary government sources.