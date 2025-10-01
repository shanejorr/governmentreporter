# GovernmentReporter Troubleshooting Guide

This guide helps you diagnose and resolve common issues with GovernmentReporter.

## Table of Contents

- [Installation Issues](#installation-issues)
- [API Connection Problems](#api-connection-problems)
- [Database Issues](#database-issues)
- [Ingestion Problems](#ingestion-problems)
- [MCP Server Issues](#mcp-server-issues)
- [Search and Retrieval Issues](#search-and-retrieval-issues)
- [Performance Issues](#performance-issues)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Diagnostic Tools](#diagnostic-tools)

---

## Installation Issues

### uv install fails

**Problem**: `uv sync` or `uv install` fails with errors

**Solutions**:

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.11+
   ```

2. **Update uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Clear cache and retry**:
   ```bash
   rm -rf .venv
   uv cache clean
   uv sync
   ```

4. **Check for conflicting dependencies**:
   ```bash
   uv pip check
   ```

### Import errors after installation

**Problem**: `ModuleNotFoundError` or `ImportError`

**Solutions**:

1. **Verify installation**:
   ```bash
   uv run python -c "import governmentreporter; print(governmentreporter.__file__)"
   ```

2. **Check PYTHONPATH**:
   ```bash
   export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
   ```

3. **Reinstall package**:
   ```bash
   uv pip install -e . --force-reinstall
   ```

---

## API Connection Problems

### OpenAI API errors

**Problem**: OpenAI API calls fail with authentication or rate limit errors

**Symptoms**:
- `openai.AuthenticationError: Incorrect API key`
- `openai.RateLimitError: Rate limit exceeded`
- `openai.APIError: Connection error`

**Solutions**:

1. **Verify API key**:
   ```bash
   echo $OPENAI_API_KEY
   # Should start with 'sk-'
   ```

2. **Test API key manually**:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Check rate limits**:
   - Review your OpenAI usage dashboard
   - Reduce batch size: `--batch-size 25`
   - Add delays between requests

4. **Check network connectivity**:
   ```bash
   ping api.openai.com
   curl -I https://api.openai.com
   ```

5. **Update API key in .env**:
   ```bash
   nano .env
   # Update OPENAI_API_KEY=...
   ```

### CourtListener API errors

**Problem**: SCOTUS ingestion fails with API errors

**Symptoms**:
- `401 Unauthorized`
- `403 Forbidden`
- `429 Too Many Requests`

**Solutions**:

1. **Verify API token**:
   ```bash
   curl -H "Authorization: Token $COURT_LISTENER_API_TOKEN" \
     https://www.courtlistener.com/api/rest/v4/courts/
   ```

2. **Check rate limiting**:
   - CourtListener has rate limits (0.1s delay between requests)
   - Logs should show delays being respected

3. **Re-register for API access**:
   - Visit https://www.courtlistener.com/api/
   - Generate new token if needed

### Federal Register API errors

**Problem**: Executive Order ingestion fails

**Symptoms**:
- `Connection timeout`
- `503 Service Unavailable`
- No authentication issues (public API)

**Solutions**:

1. **Test API manually**:
   ```bash
   curl "https://www.federalregister.gov/api/v1/documents.json?per_page=1&conditions[type][]=PRESDOCU"
   ```

2. **Check rate limiting**:
   - Federal Register: 60 requests/minute
   - Ingester uses 1.1s delay

3. **Retry with exponential backoff**:
   - Built into FederalRegisterClient
   - Check logs for retry attempts

---

## Database Issues

### Qdrant won't start

**Problem**: Qdrant database fails to start or connect

**Symptoms**:
- `Connection refused` on port 6333
- Docker container exits immediately

**Solutions**:

1. **Check if Qdrant is running**:
   ```bash
   docker ps | grep qdrant
   # or
   curl http://localhost:6333/health
   ```

2. **Start Qdrant manually**:
   ```bash
   docker run -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant
   ```

3. **Check Docker logs**:
   ```bash
   docker logs governmentreporter-qdrant
   ```

4. **Verify port availability**:
   ```bash
   lsof -i :6333  # Check if port is in use
   ```

5. **Reset Qdrant data** (⚠️ deletes all data):
   ```bash
   docker-compose down -v
   rm -rf data/qdrant/*
   docker-compose up -d qdrant
   ```

### Qdrant connection timeout

**Problem**: Application can't connect to Qdrant

**Solutions**:

1. **Check QDRANT_HOST setting**:
   ```bash
   echo $QDRANT_HOST  # Should be 'localhost' or 'qdrant' (Docker)
   ```

2. **Test from container**:
   ```bash
   docker-compose exec mcp-server curl http://qdrant:6333/health
   ```

3. **Check network**:
   ```bash
   docker-compose ps  # Verify same network
   docker network ls
   ```

### Collection errors

**Problem**: Collections missing or corrupt

**Symptoms**:
- `Collection 'supreme_court_opinions' not found`
- Empty search results despite ingestion

**Solutions**:

1. **List collections**:
   ```bash
   curl http://localhost:6333/collections
   ```

2. **Check collection info**:
   ```bash
   curl http://localhost:6333/collections/supreme_court_opinions
   ```

3. **Recreate collection**:
   ```python
   from governmentreporter.database.qdrant import QdrantDBClient
   client = QdrantDBClient()
   client.delete_collection("supreme_court_opinions")
   # Re-run ingestion
   ```

4. **Verify embeddings dimension**:
   - Should be 1536 for text-embedding-3-small
   - Check collection config matches

---

## Ingestion Problems

### Ingestion stuck or slow

**Problem**: Document ingestion takes too long or appears frozen

**Solutions**:

1. **Check progress**:
   ```bash
   tail -f logs/ingestion.log
   ```

2. **Verify progress database**:
   ```bash
   sqlite3 data/progress/scotus_ingestion.db \
     "SELECT status, COUNT(*) FROM documents GROUP BY status;"
   ```

3. **Monitor API calls**:
   ```bash
   # Watch for rate limiting messages
   grep -i "rate" logs/ingestion.log
   ```

4. **Reduce batch size**:
   ```bash
   uv run governmentreporter ingest scotus \
     --start-date 2024-01-01 \
     --end-date 2024-12-31 \
     --batch-size 25  # Smaller batches
   ```

5. **Check system resources**:
   ```bash
   top  # CPU usage
   df -h  # Disk space
   free -h  # Memory
   ```

### Duplicate documents

**Problem**: Same documents ingested multiple times

**Solutions**:

1. **Check duplicate detection**:
   - Built-in detection uses deterministic IDs
   - Review `QdrantIngestionClient.document_exists()`

2. **Clear progress and re-ingest**:
   ```bash
   rm data/progress/scotus_ingestion.db
   # Re-run ingestion - will check Qdrant for existing docs
   ```

3. **Manually check for duplicates**:
   ```python
   from governmentreporter.database.qdrant import QdrantDBClient
   client = QdrantDBClient()
   # Query by document_id to find duplicates
   ```

### Chunking errors

**Problem**: Documents fail during chunking

**Symptoms**:
- `ValueError: Chunk text too small`
- Malformed chunks in database

**Solutions**:

1. **Check chunking configuration**:
   ```bash
   # Review environment variables
   echo $RAG_SCOTUS_MIN_TOKENS
   echo $RAG_SCOTUS_TARGET_TOKENS
   echo $RAG_SCOTUS_MAX_TOKENS
   ```

2. **Test chunking manually**:
   ```python
   from governmentreporter.processors.chunking import chunk_supreme_court_opinion
   result = chunk_supreme_court_opinion(opinion_text, opinion_type="majority")
   ```

3. **Adjust token limits**:
   ```bash
   export RAG_SCOTUS_MIN_TOKENS=300  # Lower minimum
   ```

### Metadata extraction fails

**Problem**: GPT-5-nano extraction fails or returns empty metadata

**Solutions**:

1. **Check GPT-5-nano availability**:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY" | grep gpt-5
   ```

2. **Test extraction manually**:
   ```python
   from governmentreporter.processors.llm_extraction import generate_scotus_llm_fields
   metadata = generate_scotus_llm_fields(sample_text, case_name="Test v. Example")
   ```

3. **Check prompt length**:
   - Prompts too long may fail
   - Check token counts in logs

4. **Fallback to minimal metadata**:
   - Ingestion continues with basic metadata if LLM fails
   - Check warning logs

---

## MCP Server Issues

### Server won't start

**Problem**: MCP server fails to start

**Symptoms**:
- Process exits immediately
- No logs generated

**Solutions**:

1. **Run with debug logging**:
   ```bash
   export MCP_LOG_LEVEL=DEBUG
   uv run governmentreporter server
   ```

2. **Check dependencies**:
   ```bash
   uv run python -c "import mcp; import qdrant_client; print('OK')"
   ```

3. **Verify configuration**:
   ```bash
   uv run python -c "from governmentreporter.server.config import ServerConfig; print(ServerConfig())"
   ```

4. **Check port conflicts**:
   - MCP protocol uses stdio (no port needed for Claude Desktop)
   - If exposing HTTP, check port availability

### Tools not appearing in Claude Desktop

**Problem**: Claude doesn't see MCP tools

**Solutions**:

1. **Verify Claude Desktop config**:
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Check config format**:
   ```json
   {
     "mcpServers": {
       "governmentreporter": {
         "command": "uv",
         "args": ["run", "governmentreporter", "server"],
         "cwd": "/path/to/governmentreporter"
       }
     }
   }
   ```

3. **Restart Claude Desktop completely**:
   - Cmd+Q (macOS) or close from system tray
   - Relaunch

4. **Check server logs**:
   ```bash
   tail -f logs/mcp_server.log
   ```

5. **Test server independently**:
   ```bash
   uv run python -m governmentreporter.server
   # Should show initialization messages
   ```

### Search returns no results

**Problem**: MCP search tools return empty results

**Solutions**:

1. **Verify data exists**:
   ```bash
   uv run governmentreporter query "constitutional law"
   ```

2. **Check collection names**:
   ```bash
   curl http://localhost:6333/collections
   ```

3. **Test search manually**:
   ```python
   from governmentreporter.database.qdrant import QdrantDBClient
   from governmentreporter.processors.embeddings import generate_embedding

   client = QdrantDBClient()
   query_vector = generate_embedding("test query")
   results = client.semantic_search(
       collection_name="supreme_court_opinions",
       query_vector=query_vector,
       limit=5
   )
   print(len(results))
   ```

4. **Re-index documents**:
   - May need to re-run ingestion

---

## Search and Retrieval Issues

### Relevance scores too low

**Problem**: Search returns results with poor relevance

**Solutions**:

1. **Check embedding model**:
   - Ensure consistent model (text-embedding-3-small)
   - Don't mix embedding models

2. **Refine search query**:
   - More specific queries get better results
   - Use legal terminology

3. **Adjust score threshold**:
   ```python
   # In handlers, filter by minimum score
   results = [r for r in results if r['score'] > 0.7]
   ```

4. **Review chunk quality**:
   - Check if chunks are properly formed
   - Verify overlap strategy

### Search too slow

**Problem**: Semantic search takes too long

**Solutions**:

1. **Reduce search limit**:
   ```bash
   export MCP_DEFAULT_SEARCH_LIMIT=5
   ```

2. **Optimize Qdrant**:
   - Use HNSW index (default)
   - Adjust `ef_construct` and `m` parameters

3. **Enable caching**:
   ```bash
   export MCP_ENABLE_CACHE=true
   ```

4. **Monitor query time**:
   ```bash
   grep "Search took" logs/mcp_server.log
   ```

### Document retrieval fails

**Problem**: `get_document_by_id` returns None or errors

**Solutions**:

1. **Verify document ID format**:
   - SCOTUS: `scotus_{opinion_id}_chunk_{index}`
   - EO: `eo_{doc_number}_chunk_{index}`

2. **Check collection name**:
   ```bash
   curl "http://localhost:6333/collections/supreme_court_opinions/points/{point_id}"
   ```

3. **List points in collection**:
   ```python
   from qdrant_client import QdrantClient
   client = QdrantClient(host="localhost", port=6333)
   points = client.scroll(collection_name="supreme_court_opinions", limit=10)
   ```

---

## Performance Issues

### High memory usage

**Problem**: Application uses too much RAM

**Solutions**:

1. **Reduce batch size**:
   ```bash
   export SCOTUS_BATCH_SIZE=25
   export EO_BATCH_SIZE=25
   ```

2. **Limit concurrent operations**:
   - Process one collection at a time
   - Don't run ingestion and search simultaneously

3. **Monitor memory**:
   ```bash
   docker stats  # For containers
   top  # For host process
   ```

4. **Increase available memory**:
   ```yaml
   # docker-compose.yml
   services:
     mcp-server:
       mem_limit: 4g
   ```

### High CPU usage

**Problem**: CPU at 100% for extended periods

**Solutions**:

1. **Check what's running**:
   ```bash
   htop  # Interactive process viewer
   ```

2. **Identify bottleneck**:
   - Embeddings generation (OpenAI API calls)
   - Chunking (token counting)
   - Metadata extraction (LLM calls)

3. **Optimize ingestion**:
   - Increase delays between API calls
   - Reduce batch processing

4. **Profile code**:
   ```bash
   uv run python -m cProfile -o profile.stats src/governmentreporter/cli/main.py ingest scotus --start-date 2024-01-01 --end-date 2024-01-31
   ```

### Slow ingestion

**Problem**: Ingestion takes too long

**Expected times**:
- 50-100 documents/minute typical
- Rate limited by API calls

**Solutions**:

1. **Optimize batch size**:
   - Too small: more overhead
   - Too large: memory issues
   - Optimal: 50-100 for SCOTUS, 50-100 for EO

2. **Monitor bottlenecks**:
   ```bash
   tail -f logs/ingestion.log | grep "processed"
   ```

3. **Check API rate limits**:
   - OpenAI: Tier-based limits
   - CourtListener: 0.1s between requests
   - Federal Register: 60/minute

4. **Resume interrupted ingestion**:
   - Progress tracker automatically resumes
   - No need to start over

---

## Claude Desktop Integration

### Configuration file location

**Find config file**:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Common integration issues

**Problem 1**: Tools don't appear

```bash
# Check config syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool

# Verify path
ls /path/to/governmentreporter

# Test command manually
cd /path/to/governmentreporter && uv run governmentreporter server
```

**Problem 2**: Server crashes on Claude startup

```bash
# Check logs in Console.app (macOS)
# Or check Claude Desktop logs

# Test server standalone
uv run governmentreporter server --help
```

**Problem 3**: Environment variables not loaded

```bash
# Ensure .env file exists in project directory
ls /path/to/governmentreporter/.env

# Or specify in Claude config:
{
  "mcpServers": {
    "governmentreporter": {
      "command": "uv",
      "args": ["run", "governmentreporter", "server"],
      "cwd": "/path/to/governmentreporter",
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

---

## Diagnostic Tools

### Quick health check script

```bash
#!/bin/bash
# health_check.sh - Comprehensive system check

echo "=== GovernmentReporter Health Check ==="

# Check Python version
echo -n "Python version: "
python --version

# Check uv
echo -n "uv installed: "
uv --version || echo "NOT INSTALLED"

# Check environment variables
echo "Environment variables:"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo "  COURT_LISTENER_API_TOKEN: ${COURT_LISTENER_API_TOKEN:0:10}..."

# Check Qdrant
echo -n "Qdrant health: "
curl -s http://localhost:6333/health || echo "FAILED"

# Check collections
echo "Qdrant collections:"
curl -s http://localhost:6333/collections | python -m json.tool

# Check disk space
echo "Disk space:"
df -h | grep -E '(Filesystem|qdrant|progress)'

# Check logs
echo "Recent errors:"
tail -20 logs/errors.log 2>/dev/null || echo "No error log found"

echo "=== Health Check Complete ==="
```

### Database inspection

```python
# inspect_db.py - Check database contents
from governmentreporter.database.qdrant import QdrantDBClient

client = QdrantDBClient()

# List collections
collections = client.list_collections()
print(f"Collections: {collections}")

# Get collection stats
for collection in collections:
    info = client.get_collection_info(collection['name'])
    print(f"\n{collection['name']}:")
    print(f"  Points: {info.get('points_count', 0)}")
    print(f"  Vectors: {info.get('vectors_count', 0)}")
```

### Progress tracking inspection

```bash
# Check ingestion progress
sqlite3 data/progress/scotus_ingestion.db << EOF
.headers on
.mode column
SELECT status, COUNT(*) as count FROM documents GROUP BY status;
SELECT * FROM documents WHERE status='failed' LIMIT 10;
EOF
```

### Log analysis

```bash
# Find errors in logs
grep -i error logs/*.log

# Count log levels
grep -c INFO logs/governmentreporter.log
grep -c ERROR logs/governmentreporter.log

# Recent activity
tail -100 logs/governmentreporter.log

# Specific component logs
grep "governmentreporter.server" logs/governmentreporter.log | tail -50
```

---

## Getting More Help

If these troubleshooting steps don't resolve your issue:

1. **Check existing issues**: https://github.com/yourusername/governmentreporter/issues
2. **Open a new issue** with:
   - Detailed problem description
   - Error messages (full stack traces)
   - Environment info (OS, Python version, Docker version)
   - Steps to reproduce
   - Relevant log excerpts
3. **Community discussion**: https://github.com/yourusername/governmentreporter/discussions
4. **Email support**: support@governmentreporter.example

---

## Preventive Maintenance

### Regular checks

- Monitor disk space (Qdrant database grows over time)
- Review logs for recurring errors
- Update dependencies monthly
- Rotate logs regularly
- Backup databases weekly

### Best practices

- Use version control for configuration
- Document custom changes
- Test updates in staging before production
- Keep API keys secure
- Monitor API usage and costs

---

**Last Updated**: 2025-01-01
**Version**: 0.1.0
