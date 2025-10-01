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
# Using Docker Compose
docker-compose --profile ingestion up scotus-ingester

# Or locally
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### Ingest Executive Orders

```bash
# Using Docker Compose
docker-compose --profile ingestion up eo-ingester

# Or locally
uv run governmentreporter ingest eo \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

**Note**: Ingestion can take a while depending on the date range. The system will track progress and resume if interrupted.

---

## Testing the Search

### Command Line Testing

```bash
# Search across all documents
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

**Step 4: Test it!**

Ask Claude:
> "Search for recent Supreme Court cases about environmental regulation"

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
docker-compose --profile ingestion up scotus-ingester
```

### Ingestion fails

```bash
# Check API keys
echo $OPENAI_API_KEY

# View ingestion logs
docker-compose logs scotus-ingester

# Check progress database
sqlite3 data/progress/scotus_ingestion.db \
  "SELECT status, COUNT(*) FROM documents GROUP BY status;"
```

### Claude Desktop can't see tools

1. Verify config file syntax (use JSON validator)
2. Check that `cwd` path is correct
3. Completely restart Claude Desktop (Cmd+Q)
4. Check Console.app (macOS) for errors

---

## Performance Tips

### Faster Ingestion

```bash
# Increase batch size
docker-compose --profile ingestion up scotus-ingester \
  --env SCOTUS_BATCH_SIZE=100

# Or in command
uv run governmentreporter ingest scotus \
  --start-date 2024-01-01 \
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

## Next Steps

1. **Ingest more data** - Expand your date ranges
2. **Explore MCP tools** - Try different search filters
3. **Read the docs** - Check out [DEPLOYMENT.md](DEPLOYMENT.md) for advanced configuration
4. **Join the community** - Ask questions, report issues

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
| Start all services | `docker-compose up -d` |
| Stop all services | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Ingest SCOTUS | `docker-compose --profile ingestion up scotus-ingester` |
| Ingest EOs | `docker-compose --profile ingestion up eo-ingester` |
| Test search | `uv run governmentreporter query "test"` |
| Check health | `curl http://localhost:6333/health` |

---

## Getting Help

- **Issues**: https://github.com/yourusername/governmentreporter/issues
- **Discussions**: https://github.com/yourusername/governmentreporter/discussions
- **Documentation**: Full docs in the repository

---

**Happy searching! 🔍**
