# Script Updates for Hierarchical Chunking System

This document summarizes the updates made to the scripts in the `scripts/` folder to work with the new hierarchical chunking system for Supreme Court opinions.

## Updated Scripts

### 1. `scripts/download_scotus_bulk.py` ✅ UPDATED

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

### 2. `src/governmentreporter/processors/scotus_bulk.py` ✅ UPDATED

**Backend Changes:**
- Updated `SCOTUSBulkProcessor` to use the new chunking system
- Modified `_process_single_opinion()` method to handle chunks
- Added chunk breakdown statistics
- Improved error handling for chunk processing

## New Test Scripts

### 3. `scripts/test_opinion_chunking.py` ✅ NEW

**Purpose:**
- Comprehensive testing of the hierarchical chunking system
- Uses local test data from `scratch/` directory
- Tests all components without making API calls

**Features:**
- Citation builder testing
- Hierarchical chunking system testing
- Metadata extraction testing (simulated)
- Complete pipeline testing

### 4. `scripts/test_updated_process.py` ✅ NEW

**Purpose:**
- Tests the chunking system with mocked data
- Uses mocking to simulate API calls and database operations
- Verifies the chunking system works correctly

## Script Compatibility

### ✅ Fully Updated Scripts
- `download_scotus_bulk.py` - Now uses hierarchical chunking
- `test_opinion_chunking.py` - New comprehensive test script
- `test_updated_process.py` - New script validation test

### ℹ️ Legacy Script (Still Works)
- `test_pipeline.py` - Original test script, still functional for basic testing

## Usage Examples

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