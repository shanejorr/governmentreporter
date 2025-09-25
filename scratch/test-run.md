# Testing Guide for Ingestion Scripts

This guide provides step-by-step instructions for testing the executive orders and Supreme Court opinions ingestion scripts. Follow these steps to ensure the scripts are working correctly with clean databases.

## Prerequisites

Before running the tests, ensure you have:
- The GovernmentReporter repository set up with dependencies installed (`uv sync`)
- API tokens configured (especially `COURT_LISTENER_API_TOKEN` for SCOTUS ingestion)
- Terminal access to run commands

---

## 1. Clear/Empty the Databases

Before testing, it's important to start with clean databases to ensure accurate results.

### Clear Qdrant Vector Database

The Qdrant database stores the document chunks and embeddings. Clear it completely:

```bash
# Option 1: Remove the entire Qdrant database directory
rm -rf ./qdrant_db

# Option 2: Keep the directory but clear all contents
rm -rf ./qdrant_db/*

# Verify it's gone
ls -la ./qdrant_db 2>/dev/null || echo "Qdrant DB directory removed"
```

### Clear SQLite Progress Tracking Databases

The SQLite databases track ingestion progress and allow resuming interrupted jobs. Remove them:

```bash
# Remove both progress tracking databases
rm -f executive_orders_ingestion.db
rm -f scotus_ingestion.db

# Verify they're gone
ls -la *.db 2>/dev/null || echo "No .db files found"
```

---

## 2. Run Ingestion Scripts

Run each script to ingest documents from the past month. Start with dry runs to test without storing data.

### Executive Orders Ingestion

#### Dry Run (Recommended First)

Test the script without actually storing documents in Qdrant:

```bash
# Dry run - processes documents but doesn't store them
uv run python scripts/ingestion/ingest_executive_orders.py \
  --start-date 2025-08-11 \
  --end-date 2025-09-11 \
  --batch-size 25 \
  --dry-run \
  --verbose
```

#### Full Run

Once the dry run succeeds, run the actual ingestion:

```bash
# Full ingestion - stores documents in Qdrant
uv run python scripts/ingestion/ingest_executive_orders.py \
  --start-date 2021-09-01 \
  --end-date 2025-09-11 \
  --batch-size 25 \
  --verbose
```

**Parameters explained:**
- `--start-date`: Beginning of date range (YYYY-MM-DD format)
- `--end-date`: End of date range (inclusive)
- `--batch-size`: Number of documents to process at once (25 is a good default)
- `--verbose`: Show detailed logging output
- `--dry-run`: Process documents without storing them (useful for testing)

### Supreme Court Opinions Ingestion

#### Dry Run

Test without storing:

```bash
# Dry run for SCOTUS opinions
uv run python scripts/ingestion/ingest_scotus.py \
  --start-date 2025-08-11 \
  --end-date 2025-09-11 \
  --batch-size 50 \
  --dry-run \
  --verbose
```

#### Full Run

Run the actual ingestion:

```bash
# Full ingestion of SCOTUS opinions
uv run python scripts/ingestion/ingest_scotus.py \
  --start-date 2021-08-11 \
  --end-date 2025-09-11 \
  --batch-size 50 \
  --verbose
```

---

## 3. Verify Results

After running the scripts, verify that data was correctly stored in both databases.

### Check SQLite Progress Databases

Use SQLite commands to inspect the progress tracking databases.

#### Executive Orders Progress

```bash
# Summary of document processing status
sqlite3 executive_orders_ingestion.db \
  "SELECT status, COUNT(*) as count FROM document_progress GROUP BY status;"

# View ingestion run details
sqlite3 executive_orders_ingestion.db \
  "SELECT * FROM ingestion_runs;"

# Total document count
sqlite3 executive_orders_ingestion.db \
  "SELECT COUNT(*) as total_docs FROM document_progress;"

# Check for any failed documents
sqlite3 executive_orders_ingestion.db \
  "SELECT document_id, error_message FROM document_progress WHERE status='failed' LIMIT 10;"

# View sample of completed documents
sqlite3 executive_orders_ingestion.db \
  "SELECT document_id, processing_time_ms FROM document_progress WHERE status='completed' LIMIT 5;"
```

#### SCOTUS Opinions Progress

```bash
# Summary of document processing status
sqlite3 scotus_ingestion.db \
  "SELECT status, COUNT(*) as count FROM document_progress GROUP BY status;"

# View ingestion run details
sqlite3 scotus_ingestion.db \
  "SELECT * FROM ingestion_runs;"

# Total document count
sqlite3 scotus_ingestion.db \
  "SELECT COUNT(*) as total_docs FROM document_progress;"

# Check for any failed documents
sqlite3 scotus_ingestion.db \
  "SELECT document_id, error_message FROM document_progress WHERE status='failed' LIMIT 10;"
```

### Check Qdrant Vector Database

Verify that document chunks were stored with embeddings and metadata.

#### Using Python Script

Create a test script or run this interactively:

```bash
uv run python scratch/check_quadrant.py > scratch/check_quadrant.txt
```

---

## Expected Results

After successful ingestion, you should see:

### Executive Orders
- **SQLite**: Status should show documents as "completed"
- **Qdrant**: Collection should contain multiple chunks (usually 5-15 per order)
- **Metadata**: Each chunk should have title, date, agencies, topics, and other fields

### Supreme Court Opinions
- **SQLite**: Status should show opinions as "completed"
- **Qdrant**: Collection should contain multiple chunks (usually 10-50 per opinion)
- **Metadata**: Each chunk should have case name, citation, date, and other legal metadata

---

## Troubleshooting

### Common Issues and Solutions

1. **No documents found in date range**
   - Try a wider date range or check if documents exist for those dates
   - Executive orders are sporadic; not every day has orders

2. **API token errors**
   - Ensure `COURT_LISTENER_API_TOKEN` is set correctly
   - Check token validity at https://www.courtlistener.com/

3. **"Module not found" errors**
   - Run `uv sync` to install dependencies
   - Ensure you're in the project root directory

4. **Qdrant connection errors**
   - The Qdrant database directory will be created automatically
   - Check disk space if writes are failing

5. **Script interruption**
   - Scripts support resuming - just re-run the same command
   - Progress is tracked in SQLite, so completed documents won't be reprocessed

### Checking Logs

Both scripts provide detailed output when run with `--verbose`. The output includes:
- Number of documents found
- Processing progress with ETA
- Success/failure counts
- Final statistics

### Testing Small Batches

For initial testing, use smaller date ranges and batch sizes:

```bash
# Test with just a few days and small batches
uv run python scripts/ingestion/ingest_executive_orders.py \
  --start-date 2025-09-01 \
  --end-date 2025-09-05 \
  --batch-size 1 \
  --verbose
```

---

## Clean Up After Testing

To reset everything and start fresh:

```bash
# Remove all databases and progress tracking
rm -rf ./qdrant_db
rm -f executive_orders_ingestion.db
rm -f scotus_ingestion.db

# Verify clean state
echo "Checking for databases..."
ls -la ./qdrant_db 2>/dev/null || echo "✓ Qdrant DB removed"
ls -la *.db 2>/dev/null || echo "✓ SQLite DBs removed"
```

---

## Notes

- **Processing Time**: Expect ~10-30 seconds per document depending on size
- **Storage**: Each document creates multiple chunks (5-50 depending on length)
- **Rate Limits**: Scripts respect API rate limits automatically
- **Memory Usage**: Batch processing keeps memory usage reasonable
- **Network**: Requires internet access to fetch documents and generate embeddings
- **Costs**: Embedding generation uses OpenAI API (text-embedding-3-small model)
