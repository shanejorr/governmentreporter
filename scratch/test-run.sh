#!/bin/bash

# Full ingestion pipeline script
# Cleans databases, runs executive orders and SCOTUS ingestion, then checks Qdrant

set -e  # Exit on any error

echo "Starting full ingestion pipeline..."

# ====================================
# Clean up existing databases
# ====================================
echo "Removing existing databases..."

# Remove all databases and progress tracking
rm -rf ./qdrant_db
rm -f executive_orders_ingestion.db
rm -f scotus_ingestion.db

# Verify clean state
echo "Checking for databases..."
ls -la ./qdrant_db 2>/dev/null || echo "✓ Qdrant DB removed"
ls -la *.db 2>/dev/null || echo "✓ SQLite DBs removed"

# ====================================
# Ingest Executive Orders
# ====================================
echo "Starting Executive Orders ingestion..."

uv run python scripts/ingestion/ingest_executive_orders.py \
  --start-date 2025-09-01 \
  --end-date 2025-09-11 \
  --batch-size 25 \
  --verbose

echo "✓ Executive Orders ingestion completed"

# ====================================
# Ingest SCOTUS Opinions
# ====================================
echo "Starting SCOTUS opinions ingestion..."

uv run python scripts/ingestion/ingest_scotus.py \
  --start-date 2025-08-11 \
  --end-date 2025-09-11 \
  --batch-size 50 \
  --verbose

echo "✓ SCOTUS opinions ingestion completed"

# ====================================
# Check Qdrant Database
# ====================================
echo "Checking Qdrant database status..."

uv run python scratch/check_quadrant.py > scratch/check_quadrant.txt

echo "✓ Qdrant check completed - results saved to scratch/check_quadrant.txt"
echo "Full ingestion pipeline completed successfully!"
