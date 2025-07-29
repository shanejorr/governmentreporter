# GovernmentReporter

An MCP (Model Context Protocol) server that provides LLMs with access to the latest US federal government publications through retrieval augmented generation (RAG) using **hierarchical document chunking**.

## Overview

GovernmentReporter creates a ChromaDB vector database storing semantic embeddings and rich metadata for hierarchically chunked US federal Supreme Court opinions, Executive Orders, and federal legislation. The system uses **intelligent chunking** to break down Supreme Court opinions by opinion type (syllabus, majority, concurring, dissenting) and sections, enabling precise legal research and retrieval. Rather than storing full document text, the system uses on-demand API retrieval to access current documents from authoritative government sources.

## Features

### 🧩 Hierarchical Document Chunking
- **Opinion Type Separation**: Automatically identifies syllabus, majority, concurring, and dissenting opinions
- **Section-Level Granularity**: Chunks opinions by legal sections (I, II, III) and subsections (A, B, C)
- **Justice Attribution**: Concurring and dissenting opinions properly attributed to specific justices
- **Smart Token Management**: Target 400-800 tokens per chunk while preserving paragraph integrity

### 📊 Rich Legal Metadata  
- **Legal Topics**: AI-extracted primary areas of law (Constitutional Law, Administrative Law, etc.)
- **Constitutional Provisions**: Precise citations (Art. I, § 9, cl. 7, First Amendment, etc.)
- **Statutes Interpreted**: Bluebook format citations (12 U.S.C. § 5497, 42 U.S.C. § 1983)
- **Key Legal Questions**: Specific questions the court addressed
- **Court Holdings**: Extracted from syllabus and decisions

### 🚀 Advanced Capabilities
- **Comprehensive Government Data**: Indexes US Supreme Court opinions, Executive Orders, and federal legislation
- **Fresh Data Guarantee**: Retrieves latest document text on-demand from government APIs
- **Semantic Search**: Vector database enables intelligent document discovery at chunk level
- **Cost-Effective Storage**: Stores only embeddings and metadata, not full text
- **MCP Integration**: Compatible with LLMs that support the Model Context Protocol
- **Bulk Processing**: Automated pipeline for processing large datasets (10,000+ Supreme Court opinions)
- **Resumable Operations**: Progress tracking and error recovery for long-running processes
- **Programmatic API**: Reusable library components for custom data processing workflows

## Architecture

- **Language**: Python
- **Vector Database**: ChromaDB (embeddings + metadata only)
- **Cloud LLM**: Gemini 2.5 Flash-Lite API for metadata generation
- **Government APIs**: 
  - CourtListener API (Supreme Court opinions)
  - Federal Register API (Executive Orders)
  - Congress.gov API (Federal legislation)
- **Development**: VS Code with Claude Code support
- **Protocol**: Model Context Protocol (MCP)

## Data Flow

### 1. **Hierarchical Document Processing**:
   - Fetch documents from government APIs (CourtListener, Federal Register, Congress.gov)
   - **Intelligent Chunking**: Break down Supreme Court opinions by:
     - Opinion type (syllabus, majority, concurring, dissenting)
     - Legal sections (I, II, III) and subsections (A, B, C)
     - Justice attribution for concurring/dissenting opinions
   - **Rich Metadata Extraction**: Use Gemini 2.5 Flash-Lite to extract:
     - Legal topics and key questions
     - Constitutional provisions and statutes cited
     - Court holdings and legal reasoning
   - Generate embeddings for each chunk (400-800 tokens)
   - Store chunk embeddings + metadata in ChromaDB

### 2. **Semantic Search & Retrieval**:
   - Convert user query to embedding
   - Search ChromaDB for semantically similar **chunks**
   - Retrieve chunk metadata with opinion type, justice, section info
   - Make API calls to fetch current full text from authoritative sources
   - Return contextually relevant legal content to LLM

### 3. **Chunk-Aware Query Results**:
   - Users can search specifically within syllabus, majority, or dissenting opinions
   - Results include precise section references and justice attribution
   - Legal metadata enables topic-specific and citation-based searches

## Prerequisites

- Python 3.8+
- Google API key for Gemini 2.5 Flash-Lite
- macOS (tested on Apple M2 Pro)
- 8GB+ RAM recommended
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

3. **Setup Google API key**
   ```bash
   # Set up your Google API key as environment variable
   export GOOGLE_API_KEY="your-api-key-here"
   
   # Or add to your .env file
   echo "GOOGLE_API_KEY=your-api-key-here" >> .env
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

### Quick Start - Process Single Opinion

```bash
# Process a single opinion with hierarchical chunking
python main.py process 9973155

# Alternative using dedicated script
python scripts/process_scotus_opinion.py 9973155
```

### Hierarchical Chunking Operations

```bash
# Test the chunking system with example data
python scripts/test_opinion_chunking.py

# Process specific case (Consumer Financial Protection Bureau v. Community Financial Services)
python scripts/process_scotus_opinion.py 9973155

# Expected output:
# ✅ Generated 52 chunks
# 📊 Chunk breakdown:
#    - Syllabus: 2 chunks  
#    - Majority: 23 chunks
#    - Concurring: 27 chunks (by Barrett, Jackson)
# 📋 Case: Consumer Financial Protection Bureau v. Community Financial Services Assn.
# 📄 Citation: 601 U.S. 416 (2024)
```

### Bulk Data Processing with Chunking

For initial setup or comprehensive data collection, use the bulk processing tools:

```bash
# Download and process all Supreme Court opinions since 1900 (with chunking)
uv run python scripts/download_scotus_bulk.py

# Check total available opinions
uv run python scripts/download_scotus_bulk.py --count-only

# Process limited number for testing chunking system
uv run python scripts/download_scotus_bulk.py --max-opinions 10

# Check current processing progress
uv run python scripts/download_scotus_bulk.py --stats

# Custom date range and collection
uv run python scripts/download_scotus_bulk.py --since-date 2020-01-01 --collection-name recent_scotus
```

### Programmatic Usage

The chunking system can be used programmatically:

```python
from governmentreporter.processors import SCOTUSOpinionProcessor, SCOTUSBulkProcessor

# Process single opinion with hierarchical chunking
processor = SCOTUSOpinionProcessor()
chunks = processor.process_opinion(9973155)

print(f"Generated {len(chunks)} chunks")
for chunk in chunks[:3]:  # Show first 3 chunks
    print(f"- {chunk.opinion_type.title()} by {chunk.justice or 'Court'}")
    print(f"  Section: {chunk.section or 'N/A'}")
    print(f"  Topics: {chunk.legal_topics[:2]}")  # First 2 topics
    print(f"  Text: {chunk.text[:100]}...\n")

# Bulk processing with chunking
bulk_processor = SCOTUSBulkProcessor(
    since_date="2020-01-01",
    rate_limit_delay=1.0
)

# Get processing statistics
stats = bulk_processor.get_processing_stats()
print(f"Progress: {stats['progress_percentage']:.1f}%")

# Run bulk processing (now with chunking)
results = bulk_processor.process_all_opinions(max_opinions=100)
print(f"Success rate: {results['success_rate']:.1%}")
```

### Data Pipeline

The system follows a three-step process:

1. **Initial Indexing**: 
   - Fetches documents from government APIs
   - Generates semantic embeddings from full text
   - Creates lightweight metadata using Gemini 2.5 Flash-Lite
   - Stores embeddings + metadata in ChromaDB

2. **Semantic Search**:
   - User query converted to embedding
   - ChromaDB returns similar document metadata
   - System identifies relevant government documents

3. **Real-time Retrieval**:
   - Makes API calls using stored identifiers
   - Fetches current document text from authoritative sources
   - Returns fresh content to LLM via MCP

### Example Query Flows

#### General Legal Research
```
User: "Find recent Supreme Court decisions about environmental regulation"

1. Query embedded and searched in ChromaDB across all chunks
2. Matching chunks returned with metadata:
   - Case names, citations, dates
   - Opinion type (syllabus, majority, concurring, dissenting)
   - Justice attribution and section references
   - Legal topics: ["Environmental Law", "Administrative Law", "Commerce Clause"]
3. Full text retrieved from CourtListener API for top matches
4. Contextually relevant Supreme Court content provided to LLM
```

#### Opinion-Type Specific Search
```
User: "Show me dissenting opinions about free speech from Justice Thomas"

1. Query filtered for dissenting opinions with justice="Thomas"
2. Chunks matching free speech topics returned with:
   - Specific dissenting opinion text
   - Constitutional provisions cited (First Amendment)
   - Section references within the dissent
3. Justice Thomas's specific dissenting arguments provided
```

#### Citation and Legal Analysis
```
User: "Find cases interpreting 42 U.S.C. § 1983"

1. Query searches statute_interpreted metadata field
2. Returns chunks citing this specific statute with:
   - Court's interpretation in majority opinions
   - Concurring/dissenting views on the statute
   - Related constitutional provisions
3. Comprehensive statutory analysis across multiple cases provided
```

## Hierarchical Chunking System

### Supreme Court Opinion Structure

GovernmentReporter automatically identifies and chunks Supreme Court opinions using sophisticated pattern recognition:

#### Opinion Types Detected:
- **Syllabus**: Court's official summary (usually 2-4 chunks)
- **Majority Opinion**: Main opinion of the court (10-30 chunks depending on length)
- **Concurring Opinions**: Justices agreeing with result but with different reasoning
- **Dissenting Opinions**: Justices disagreeing with the majority

#### Section Detection:
- **Major Sections**: Roman numerals (I, II, III, IV)
- **Subsections**: Capital letters (A, B, C, D)
- **Smart Chunking**: Preserves paragraph boundaries and legal arguments

#### Metadata Per Chunk:
```json
{
  "text": "The actual chunk content...",
  "opinion_type": "majority",
  "justice": "Thomas",
  "section": "II.A", 
  "chunk_index": 3,
  "case_name": "Consumer Financial Protection Bureau v. Community Financial Services Assn.",
  "citation": "601 U.S. 416 (2024)",
  "legal_topics": ["Constitutional Law", "Administrative Law", "Appropriations Clause"],
  "constitutional_provisions": ["Art. I, § 9, cl. 7"],
  "statutes_interpreted": ["12 U.S.C. § 5497(a)(1)"],
  "holding": "Congress' statutory authorization satisfies the Appropriations Clause"
}
```

### Processing Pipeline

1. **API Retrieval**: Fetch opinion and cluster data from CourtListener
2. **Opinion Type Detection**: Use regex patterns to identify different opinion types
3. **Section Parsing**: Detect Roman numeral sections and lettered subsections
4. **Intelligent Chunking**: Target 400-800 tokens while preserving legal structure
5. **Metadata Extraction**: Use Gemini 2.5 Flash-Lite for rich legal metadata
6. **Citation Formatting**: Build proper bluebook citations from cluster data
7. **Embedding Generation**: Create semantic embeddings for each chunk
8. **Database Storage**: Store chunks with complete metadata in ChromaDB

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
- Gemini API configuration for metadata generation
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
- 8GB RAM (reduced requirement due to cloud-based LLM)
- 5GB free storage (significantly reduced due to metadata-only approach)
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