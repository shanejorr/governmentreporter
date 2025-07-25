# SCOTUS Opinion Processing Pipeline

This document describes the complete pipeline for processing US Supreme Court opinions using the CourtListener API, Gemini 2.5 Flash-Lite, and Google embeddings.

## Components Created

### 1. API Client (`src/governmentreporter/apis/court_listener.py`)
- Fetches opinion data from CourtListener API
- Extracts basic metadata: `id`, `date`, `plain_text`, `author_id`, etc.
- Uses API token from environment variable `COURT_LISTENER_API_TOKEN`

### 2. ChromaDB Integration (`src/governmentreporter/database/chroma_client.py`)
- Stores embeddings and metadata in ChromaDB
- Uses collection `federal_court_scotus_opinions`
- Supports similarity search and document retrieval

### 3. Gemini Metadata Generator (`src/governmentreporter/metadata/gemini_generator.py`)
- Uses Gemini 2.5 Flash-Lite API for metadata extraction
- Extracts: `summary`, `topics`, `author`, `majority`, `minority`
- Uses API key from environment variable `GOOGLE_GEMINI_API_KEY`

### 4. Google Embeddings (`src/governmentreporter/utils/embeddings.py`)
- Generates vector embeddings using Google's text-embedding-004 model
- Supports both document and query embeddings
- Uses same API key as Gemini

## Usage

### Environment Setup
Create a `.env` file with:
```
COURT_LISTENER_API_TOKEN=your_token_here
GOOGLE_GEMINI_API_KEY=your_key_here
```

### Processing a Single Opinion
```bash
# Using the main processing script
uv run python process_scotus_opinion.py 9973155

# Or using the provided data
uv run python test_pipeline.py
```

### Example Output
The pipeline extracts:
- **Basic metadata**: Opinion ID, date, text length, author ID
- **AI metadata**: 
  - Summary of issue, holding, and rationale
  - Topic tags (e.g., "constitutional law", "appropriations clause")
  - Opinion author name
  - Majority and minority justice names
- **Vector embedding**: 768-dimensional embedding for semantic search
- **Storage**: All data stored in ChromaDB for retrieval

## Test Results
The pipeline successfully:
✅ Extracts metadata from CourtListener API format  
✅ Handles AI metadata generation (with proper API keys)  
✅ Creates vector embeddings (with proper API keys)  
✅ Stores and retrieves data from ChromaDB  
✅ Provides end-to-end processing capability  

## Files Created
- `src/governmentreporter/apis/court_listener.py` - CourtListener API client
- `src/governmentreporter/database/chroma_client.py` - ChromaDB integration  
- `src/governmentreporter/metadata/gemini_generator.py` - Gemini metadata extraction
- `src/governmentreporter/utils/embeddings.py` - Google embeddings client
- `process_scotus_opinion.py` - Main processing script
- `test_pipeline.py` - Pipeline testing script

The pipeline is ready for production use with proper API credentials.