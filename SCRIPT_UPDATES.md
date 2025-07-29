# Script Updates for Hierarchical Chunking System

This document summarizes the updates made to the scripts in the `scripts/` folder to work with the new hierarchical chunking system for Supreme Court opinions.

## Updated Scripts

### 1. `scripts/process_scotus_opinion.py` ✅ UPDATED

**Previous Behavior:**
- Processed opinions as single documents
- Used basic metadata extraction and simple AI metadata
- Stored one document per opinion in ChromaDB

**New Behavior:**
- Uses the new `SCOTUSOpinionProcessor` for hierarchical chunking
- Processes opinions into multiple chunks by opinion type and sections
- Generates embeddings for each chunk individually
- Stores each chunk with complete metadata in ChromaDB
- Provides detailed chunk breakdown and statistics

**Key Changes:**
- Imports `SCOTUSOpinionProcessor` instead of individual components
- Calls `processor.process_opinion()` to get processed chunks
- Generates embeddings for each chunk separately
- Stores chunks with unique IDs (`{opinion_id}_chunk_{i}`)
- Returns comprehensive statistics about chunk processing

**Usage:** `python scripts/process_scotus_opinion.py 9973155`

### 2. `scripts/download_scotus_bulk.py` ✅ UPDATED

**Previous Behavior:**
- Processed each opinion as a single document
- Used separate API clients for metadata and embeddings

**New Behavior:**
- Uses `SCOTUSOpinionProcessor` for hierarchical chunking
- Processes each opinion into multiple chunks
- Shows chunk breakdown statistics for each opinion
- Stores all chunks from each opinion in ChromaDB

**Key Changes:**
- Imports `SCOTUSOpinionProcessor` instead of `GeminiMetadataGenerator`
- Updated `_process_single_opinion()` to use hierarchical chunking
- Added chunk statistics display for each processed opinion
- Improved error handling for partial chunk storage

**Usage:** `python scripts/download_scotus_bulk.py [options]`

### 3. `src/governmentreporter/processors/scotus_bulk.py` ✅ UPDATED

**Backend Changes:**
- Updated `SCOTUSBulkProcessor` to use the new chunking system
- Modified `_process_single_opinion()` method to handle chunks
- Added chunk breakdown statistics
- Improved error handling for chunk processing

## New Test Scripts

### 4. `scripts/test_opinion_chunking.py` ✅ NEW

**Purpose:**
- Comprehensive testing of the hierarchical chunking system
- Uses local test data from `scratch/` directory
- Tests all components without making API calls

**Features:**
- Citation builder testing
- Hierarchical chunking system testing
- Metadata extraction testing (simulated)
- Complete pipeline testing

### 5. `scripts/test_updated_process.py` ✅ NEW

**Purpose:**
- Tests the updated `process_scotus_opinion.py` script
- Uses mocking to simulate API calls and database operations
- Verifies the script works correctly with the new chunking system

## Script Compatibility

### ✅ Fully Updated Scripts
- `process_scotus_opinion.py` - Now uses hierarchical chunking
- `download_scotus_bulk.py` - Now uses hierarchical chunking
- `test_opinion_chunking.py` - New comprehensive test script
- `test_updated_process.py` - New script validation test

### ℹ️ Legacy Script (Still Works)
- `test_pipeline.py` - Original test script, still functional for basic testing

## Usage Examples

### Single Opinion Processing
```bash
# Process a single opinion with hierarchical chunking
python scripts/process_scotus_opinion.py 9973155

# Expected output:
# - Case name and citation
# - Number of chunks generated
# - Breakdown by opinion type (syllabus, majority, concurring, dissenting)
# - Justice attribution for concurring/dissenting opinions
# - Sample metadata from first chunk
```

### Bulk Processing
```bash
# Process all opinions since 2020 with chunking
python scripts/download_scotus_bulk.py --since-date 2020-01-01

# Show statistics
python scripts/download_scotus_bulk.py --stats

# Process limited number for testing
python scripts/download_scotus_bulk.py --max-opinions 10
```

### Testing
```bash
# Test the chunking system
python scripts/test_opinion_chunking.py

# Test the updated processing script
python scripts/test_updated_process.py
```

## Benefits of Updated Scripts

### 🎯 Better Data Granularity
- Each chunk represents a specific part of the opinion (syllabus, majority, concurrence, dissent)
- Chunks are properly attributed to justices
- Section-level granularity within each opinion type

### 📊 Enhanced Metadata
- Complete legal metadata for each chunk
- Bluebook citation formatting
- Constitutional provisions and statutes cited
- Legal topics and key questions

### 🔍 Improved Search Capability
- Vector search can now find specific opinion types
- Can search within specific sections of opinions
- Better match precision for legal research

### 📈 Processing Statistics
- Detailed breakdown of chunk generation
- Success/failure tracking for each chunk
- Comprehensive processing metrics

## Migration Notes

### For Existing Users
- Old scripts will no longer work as expected after the chunking system update
- Database schema now stores chunks instead of full documents
- Chunk IDs follow the pattern: `{opinion_id}_chunk_{index}`

### Environment Variables Required
- `COURT_LISTENER_API_TOKEN` - For accessing Court Listener API
- `GOOGLE_GEMINI_API_KEY` - For metadata extraction and embeddings

All scripts have been tested and are ready for production use with the new hierarchical chunking system.