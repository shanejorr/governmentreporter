# GovernmentReporter Quick Start Guide

Get GovernmentReporter running in 5 minutes! 🚀

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- CourtListener API token (optional, only for SCOTUS ingestion) ([register here](https://www.courtlistener.com/api/))

## Installation Options

### Option 1: Docker Compose (Recommended) ⭐

**Step 1: Clone the repository**
```bash
git clone https://github.com/yourusername/governmentreporter.git
cd governmentreporter
```

**Step 2: Configure environment**
```bash
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

**Step 3: Start everything**
```bash
docker-compose up -d
```

**Step 4: Verify it's running**
```bash
docker-compose ps
docker-compose logs -f mcp-server
```

Done! Your MCP server is running. 🎉

### Option 2: Local Development

**Step 1: Install dependencies**
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

**Step 2: Configure environment**
```bash
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

**Step 3: Start Qdrant**
```bash
docker run -d -p 6333:6333 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant
```

**Step 4: Start MCP server**
```bash
uv run governmentreporter server
```

Done! Server is running locally. 🎉

---

## Ingesting Data

Before you can search, you need to ingest some documents.

### Ingest Supreme Court Opinions

```bash
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
  --end-date 2024-12-31

# With custom batch size for faster ingestion
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --batch-size 100
```

### Ingest Executive Orders

```bash
uv run governmentreporter ingest eo \
  --start-date 2024-01-01 \
  --end-date 2024-12-31

# With custom batch size for faster ingestion
uv run governmentreporter ingest eo \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --batch-size 100
```

**Note**: Ingestion can take a while depending on the date range. The system will track progress and resume if interrupted.

---

## Testing the Search

### MCP Server Status

✅ **The MCP server is fully functional and production-ready!**

The server includes:
- 5 semantic search tools for government documents
- stdio transport (JSON-RPC 2.0)
- Qdrant vector database integration
- Optimized result formatting for LLM consumption

### Command Line Testing

```bash
# Test the MCP server locally (Ctrl+C to stop)
uv run governmentreporter server

# You should see:
# INFO - Initializing GovernmentReporter MCP Server...
# INFO - Connected to Qdrant. Available collections: [...]
# INFO - MCP server initialized successfully

# Search across all documents (alternative command-line tool)
uv run governmentreporter query "constitutional law"

# The query command will show search results from Qdrant
```

### Claude Desktop Integration

**Step 1: Locate Claude Desktop config file**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Step 2: Add MCP server configuration**

```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": ["run", "governmentreporter", "server"],
      "cwd": "/path/to/your/governmentreporter"
    }
  }
}
```

**Important**: Replace `/path/to/your/governmentreporter` with your actual project path.

**Optional**: If you don't have a `.env` file in your project, add API keys directly:
```json
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": ["run", "governmentreporter", "server"],
      "cwd": "/path/to/your/governmentreporter",
      "env": {
        "OPENAI_API_KEY": "your-openai-key-here",
        "COURT_LISTENER_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Step 3: Restart Claude Desktop**

Completely quit (Cmd+Q on macOS) and restart Claude Desktop.

**Step 4: Verify Connection**

Ask Claude:
> "What tools do you have access to?"

You should see the 5 GovernmentReporter tools listed.

**Step 5: Test it!**

Ask Claude questions like:
- "Search for recent Supreme Court cases about environmental regulation"
- "Find Executive Orders about climate policy"
- "What collections are available?"

Claude will use the MCP tools to search your indexed documents!

---

## Common Commands

### Server Management

```bash
# Start server
docker-compose up -d mcp-server

# Stop server
docker-compose down

# View logs
docker-compose logs -f mcp-server

# Restart server
docker-compose restart mcp-server
```

### Data Management

```bash
# Backup Qdrant database
docker exec governmentreporter-qdrant \
  tar czf /backup/qdrant-$(date +%Y%m%d).tar.gz \
  /qdrant/storage

# Clear all data (⚠️ destructive)
docker-compose down -v
rm -rf data/
```

### Monitoring

```bash
# Check Qdrant health
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections

# View collection stats
curl http://localhost:6333/collections/supreme_court_opinions

# Check logs for errors
tail -f logs/errors.log
```

---

## Troubleshooting

### Server won't start

```bash
# Check logs
docker-compose logs mcp-server

# Verify Qdrant is running
docker-compose ps qdrant
curl http://localhost:6333/health

# Check environment variables
docker-compose config
```

### No search results

```bash
# Verify data was ingested
curl http://localhost:6333/collections

# Check for documents
curl http://localhost:6333/collections/supreme_court_opinions

# Re-run ingestion if needed
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31
```

### Ingestion fails

```bash
# Check API keys
echo $OPENAI_API_KEY

# Check progress database
sqlite3 data/progress/scotus_ingestion.db \
  "SELECT status, COUNT(*) FROM documents GROUP BY status;"

# Re-run ingestion (it will resume from where it left off)
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31
```

### Claude Desktop can't see tools

1. **Test server locally first**: Run `uv run governmentreporter server` to verify it starts without errors
2. **Verify config file syntax**: Use a JSON validator to check `claude_desktop_config.json`
3. **Check `cwd` path**: Ensure the path to your project is absolute and correct
4. **Verify dependencies**: Run `uv sync` to ensure all packages are installed
5. **Completely restart Claude Desktop**: Use Cmd+Q on macOS, not just closing the window
6. **Check logs**: Console.app (macOS) or Event Viewer (Windows) for error messages
7. **Test with debug logging**: Add `"MCP_LOG_LEVEL": "DEBUG"` to the `env` section in config

---

## Performance Tips

### Faster Ingestion

```bash
# Increase batch size for faster processing
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --batch-size 100

# Process multiple years
uv run governmentreporter ingest scotus \
  --start-date 2020-01-01 \
  --end-date 2024-12-31 \
  --batch-size 100
```

### Faster Search

```bash
# Reduce default search limit
export MCP_DEFAULT_SEARCH_LIMIT=5

# Enable caching
export MCP_ENABLE_CACHE=true
```

### Resource Management

```bash
# Limit Docker memory
# Edit docker-compose.yml
services:
  mcp-server:
    mem_limit: 2g

# Monitor resource usage
docker stats
```

---

## MCP Tools Available

Once connected to Claude Desktop, you have access to 5 powerful tools:

1. **`search_government_documents`** - Search across all collections (SCOTUS + Executive Orders)
2. **`search_scotus_opinions`** - SCOTUS-specific search with filters (opinion type, justice, dates)
3. **`search_executive_orders`** - Executive Order search with filters (president, agencies, topics)
4. **`get_document_by_id`** - Retrieve specific document chunks by ID
5. **`list_collections`** - View available collections and statistics

All tools return results with rich metadata, relevance scores, and properly formatted citations.

---

## Next Steps

1. **Ingest more data** - Expand your date ranges to build a comprehensive database
2. **Explore MCP tools** - Try different search filters and combinations
3. **Read the docs** - Check out [README.md](README.md) for full Claude Desktop integration tutorial
4. **Advanced configuration** - Customize server settings via environment variables
5. **Join the community** - Ask questions, report issues

---

## Quick Reference

### Essential URLs

- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Qdrant API**: http://localhost:6333
- **Documentation**: [README.md](README.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)

### Key Files

- **Environment Config**: `.env`
- **Logging Config**: `logging.yaml`
- **Docker Config**: `docker-compose.yml`
- **Progress DBs**: `data/progress/*.db`
- **Qdrant Data**: `data/qdrant/`
- **Logs**: `logs/`

### Important Commands

| Task | Command |
|------|---------|
| **Start MCP server** | `uv run governmentreporter server` |
| **Start MCP server (debug)** | `uv run governmentreporter server --log-level DEBUG` |
| Start all services | `docker-compose up -d` |
| Stop all services | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Ingest SCOTUS | `uv run governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD` |
| Ingest EOs | `uv run governmentreporter ingest eo --start-date YYYY-MM-DD --end-date YYYY-MM-DD` |
| Test search | `uv run governmentreporter query "test"` |
| Check Qdrant health | `curl http://localhost:6333/health` |
| List collections | `uv run governmentreporter info collections` |

---

## Getting Help

- **Issues**: https://github.com/yourusername/governmentreporter/issues
- **Discussions**: https://github.com/yourusername/governmentreporter/discussions
- **Documentation**: Full docs in the repository

---

**Happy searching! 🔍**
