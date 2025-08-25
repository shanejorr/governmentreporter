# GovernmentReporter

A Python library for retrieving, processing, and storing US federal government publications in a Qdrant vector database for retrieval augmented generation (RAG) using **hierarchical document chunking**.

## Overview

GovernmentReporter creates a Qdrant vector database storing semantic embeddings and rich metadata for hierarchically chunked US federal Supreme Court opinions and Executive Orders. The system uses **intelligent chunking** to break down documents by their natural structure - Supreme Court opinions by opinion type (syllabus, majority, concurring, dissenting) and sections, Executive Orders by header/sections/subsections/tail - enabling precise legal research and retrieval.

## Features

### 🧩 Hierarchical Document Chunking
**Supreme Court Opinions:**
- **Opinion Type Separation**: Automatically identifies syllabus, majority, concurring, and dissenting opinions
- **Section-Level Granularity**: Chunks opinions by legal sections (I, II, III) and subsections (A, B, C)
- **Justice Attribution**: Concurring and dissenting opinions properly attributed to specific justices
- **Smart Token Management**: Target 600 tokens, max 800 tokens per chunk while preserving paragraph integrity

**Executive Orders:**
- **Structural Chunking**: Separates header, sections (Sec. 1, Sec. 2), subsections, and signature blocks
- **Section Detection**: Automatically identifies numbered sections and lettered subsections
- **Overlap Strategy**: Adds sentence overlap between chunks for context preservation
- **Compact Chunking**: Target 300 tokens, max 400 tokens per chunk for policy documents

### 📊 Rich Legal Metadata
**Supreme Court Opinions:**
- **Legal Topics**: AI-extracted primary areas of law (Constitutional Law, Administrative Law, etc.)
- **Constitutional Provisions**: Precise citations (Art. I, § 9, cl. 7, First Amendment, etc.)
- **Statutes Interpreted**: Bluebook format citations (12 U.S.C. § 5497, 42 U.S.C. § 1983)
- **Key Legal Questions**: Specific questions the court addressed
- **Court Holdings**: Extracted from syllabus and decisions
- **Vote Breakdown**: Justice voting patterns (9-0, 7-2, etc.)

**Executive Orders:**
- **Policy Summary**: Concise abstracts of executive order purpose
- **Policy Topics**: Topical tags (aviation, regulatory reform, environment, etc.)
- **Impacted Agencies**: Federal agency codes (FAA, EPA, NASA, etc.)
- **Legal Authorities**: U.S. Code and CFR citations in bluebook format
- **EO References**: Related executive orders referenced, revoked, or amended
- **Economic Sectors**: Affected industries and societal sectors

### 🚀 Advanced Capabilities
- **Comprehensive Government Data**: Indexes US Supreme Court opinions and Executive Orders
- **Fresh Data Guarantee**: Retrieves latest document text on-demand from government APIs
- **Semantic Search**: Vector database enables intelligent document discovery at chunk level
- **API-First Design**: Reusable library components for custom workflows
- **Bulk Processing**: Automated pipeline for processing large datasets (10,000+ Supreme Court opinions)
- **Resumable Operations**: Progress tracking and error recovery for long-running processes
- **Duplicate Detection**: Smart checking to avoid reprocessing existing documents
- **Programmatic API**: Reusable library components for custom data processing workflows

## Architecture

- **Language**: Python 3.11+
- **Package Manager**: uv (modern Python package manager)
- **Vector Database**: Qdrant (embeddings + metadata only)
- **AI Services**:
  - OpenAI GPT-5-nano for metadata generation
  - OpenAI text-embedding-3-small for semantic embeddings
- **Government APIs**:
  - CourtListener API (Supreme Court opinions)
  - Federal Register API (Executive Orders)
- **Development**: VS Code with Claude Code support
- **Storage**: Qdrant vector database

## Data Flow

### 1. **Hierarchical Document Processing**:
   - Fetch documents from government APIs (CourtListener, Federal Register)
   - **Intelligent Chunking**:
     - **SCOTUS Opinions**: Break down by opinion type (syllabus, majority, concurring, dissenting), legal sections (I, II, III) and subsections (A, B, C), justice attribution
     - **Executive Orders**: Break down by header, sections (Sec. 1, Sec. 2), subsections, and signature blocks
   - **Rich Metadata Extraction**: Use GPT-5-nano to extract:
     - Legal/policy topics and key questions
     - Constitutional provisions and statutes cited
     - Court holdings and policy summaries
   - Generate embeddings for each chunk (SCOTUS: 600/800 tokens, EO: 300/400 tokens)
   - Store chunk embeddings + metadata in Qdrant

### 2. **Semantic Search & Retrieval**:
   - Convert user query to embedding
   - Search Qdrant for semantically similar **chunks**
   - Retrieve chunk metadata with opinion type, justice, section info
   - Return contextually relevant legal content to LLM

### 3. **Chunk-Aware Query Results**:
   - Users can search specifically within syllabus, majority, or dissenting opinions
   - Results include precise section references and justice attribution
   - Legal metadata enables topic-specific and citation-based searches

## Prerequisites

- Python 3.11+
- uv package manager
- OpenAI API key
- CourtListener API token (free registration required)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/governmentreporter.git
   cd governmentreporter
   ```

2. **Install uv package manager** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install Python dependencies**
   ```bash
   uv sync
   ```

4. **Setup API keys**
   ```bash
   # Create .env file with required API keys
   cat > .env << EOF
   OPENAI_API_KEY="your-openai-api-key-here"
   COURT_LISTENER_API_TOKEN="your-courtlistener-token-here"
   EOF
   ```

   **Get API Keys:**
   - **OpenAI API**: Get key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **CourtListener API**: Free registration at [CourtListener](https://www.courtlistener.com/api/)

## Usage

### Quick Start - Process Documents

```bash
# Process SCOTUS opinions for testing (with date range support)
uv run python scripts/download_scotus_bulk.py --since-date 2024-01-01 --until-date 2024-12-31 --max-opinions 5

# Process Executive Orders from 2024
uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31 --max-orders 10
```

### Document Processing Operations

**SCOTUS Opinion Processing:**
```bash
# Process recent opinions with hierarchical chunking
uv run python scripts/download_scotus_bulk.py --since-date 2020-01-01 --max-opinions 10

# Expected output for a typical case:
# ✅ Generated 25 chunks
# 📊 Chunk breakdown:
#    - Syllabus: 2 chunks
#    - Majority: 15 chunks
#    - Concurring: 8 chunks (by Barrett, Jackson)
# 📋 Case: Consumer Financial Protection Bureau v. Community Financial Services Assn.
# 📄 Citation: 601 U.S. 416 (2024)
```

**Executive Order Processing:**
```bash
# Process 2024 Executive Orders
uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31

# Expected output for a typical EO:
# ✅ Generated 12 chunks
# 📊 Chunk breakdown:
#    - Header: 2 chunks
#    - Section: 8 chunks (across 5 sections)
#    - Tail: 2 chunks
# 📋 EO 14117: Promoting Access to Voting
# 📄 Document: 2024-05678
```

### Bulk Data Processing

**Supreme Court Opinions:**
```bash
# Download and process all Supreme Court opinions since 1900
uv run python scripts/download_scotus_bulk.py

# Process opinions within a specific date range
uv run python scripts/download_scotus_bulk.py --since-date 2020-01-01 --until-date 2024-12-31

# Check total available opinions in date range
uv run python scripts/download_scotus_bulk.py --since-date 2024-01-01 --until-date 2024-12-31 --count-only

# Process limited number for testing
uv run python scripts/download_scotus_bulk.py --max-opinions 10

# Check current processing progress
uv run python scripts/download_scotus_bulk.py --stats

# Custom date range and collection
uv run python scripts/download_scotus_bulk.py --since-date 2020-01-01 --until-date 2022-12-31 --collection-name recent_scotus
```

**Executive Orders:**
```bash
# Process all Executive Orders from a specific year
uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31

# Process with custom settings
uv run python scripts/process_executive_orders.py 2020-01-01 2024-12-31 --max-orders 50 --collection-name recent_eos

# Check processing statistics
uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31 --stats
```

### Programmatic Usage

The processing system can be used programmatically:

```python
from governmentreporter.processors import (
    SCOTUSOpinionProcessor, SCOTUSBulkProcessor,
    ExecutiveOrderProcessor, ExecutiveOrderBulkProcessor
)

# Process single SCOTUS opinion
scotus_processor = SCOTUSOpinionProcessor()
result = scotus_processor.process_and_store(
    document_id="9973155",
    collection_name="federal_court_scotus_opinions"
)
print(f"Generated {result['chunks_processed']} chunks")

# Process single Executive Order
eo_processor = ExecutiveOrderProcessor()
result = eo_processor.process_and_store(
    document_id="2024-05678",
    collection_name="federal-executive-orders"
)
print(f"Generated {result['chunks_processed']} chunks")

# Bulk processing with date range support
scotus_bulk = SCOTUSBulkProcessor(
    since_date="2020-01-01",
    until_date="2024-12-31"  # Optional end date
)
stats = scotus_bulk.get_processing_stats()
print(f"SCOTUS Progress: {stats['progress_percentage']:.1f}%")

eo_bulk = ExecutiveOrderBulkProcessor()
results = eo_bulk.process_executive_orders(
    start_date="2024-01-01",
    end_date="2024-12-31",
    max_orders=10
)
print(f"EO Success rate: {results['success_rate']:.1%}")
```

### Data Processing Pipeline

The system follows a structured processing pipeline:

1. **Document Fetching**:
   - SCOTUS: CourtListener API for opinion and cluster data
   - Executive Orders: Federal Register API for order data and raw text

2. **Hierarchical Chunking**:
   - SCOTUS: Split by opinion type → sections → paragraphs (600/800 tokens)
   - Executive Orders: Split by header → sections → subsections → tail (300/400 tokens)

3. **Metadata Extraction**:
   - Use GPT-5-nano to extract rich legal/policy metadata
   - Generate bluebook citations and structured metadata

4. **Embedding Generation**:
   - OpenAI text-embedding-3-small for semantic embeddings
   - Each chunk gets its own embedding vector

5. **Storage**:
   - Store chunk embeddings + metadata in Qdrant

6. **Search & Retrieval**:
   - User query converted to embedding
   - Qdrant returns similar chunk metadata
   - Fresh content can be retrieved on-demand from government APIs

### Example Query Flows

#### SCOTUS Legal Research
```
User: "Find recent Supreme Court decisions about environmental regulation"

1. Query embedded and searched in Qdrant across SCOTUS chunks
2. Matching chunks returned with metadata:
   - Case names, citations, dates
   - Opinion type (syllabus, majority, concurring, dissenting)
   - Justice attribution and section references
   - Legal topics: ["Environmental Law", "Administrative Law", "Commerce Clause"]
3. Contextually relevant Supreme Court content provided to LLM
```

#### Executive Order Policy Research
```
User: "Find Executive Orders about aviation regulatory reform"

1. Query searches Executive Order chunks in Qdrant
2. Matching chunks returned with metadata:
   - EO numbers, titles, signing dates, presidents
   - Policy topics: ["aviation", "regulatory reform", "transportation"]
   - Impacted agencies: ["FAA", "DOT"]
   - Section and subsection references
3. Relevant policy content provided to LLM
```

#### Cross-Document Legal Analysis
```
User: "Find cases and executive orders about financial regulation"

1. Query searches across both SCOTUS and EO collections
2. Returns mixed results with:
   - SCOTUS: Court interpretations and legal precedents
   - Executive Orders: Policy directives and regulatory changes
   - Related agencies, statutes, and constitutional provisions
3. Comprehensive legal and policy analysis across document types
```

## Hierarchical Chunking System

### Supreme Court Opinion Structure

GovernmentReporter automatically identifies and chunks Supreme Court opinions using sophisticated pattern recognition:

#### Opinion Types Detected:
- **Syllabus**: Court's official summary (usually 1-2 chunks)
- **Majority Opinion**: Main opinion of the court (10-25 chunks depending on length)
- **Concurring Opinions**: Justices agreeing with result but with different reasoning
- **Dissenting Opinions**: Justices disagreeing with the majority

#### Section Detection:
- **Major Sections**: Roman numerals (I, II, III, IV)
- **Subsections**: Capital letters (A, B, C, D)
- **Smart Chunking**: Target 600 tokens, max 800 tokens while preserving paragraph boundaries

#### SCOTUS Metadata Per Chunk:
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
  "holding": "Congress' statutory authorization satisfies the Appropriations Clause",
  "vote_breakdown": "7-2"
}
```

### Executive Order Structure

#### Document Parts Detected:
- **Header**: Title, authority, preamble ("it is hereby ordered")
- **Sections**: Numbered sections (Sec. 1, Sec. 2, etc.) with titles
- **Subsections**: Lettered subsections (a), (b), (c) and numbered items (1), (2)
- **Tail**: Signature block, filing information

#### EO Processing Features:
- **Smart Chunking**: Target 300 tokens, max 400 tokens with overlap between chunks
- **Section Titles**: Preserved (e.g., "Sec. 2. Regulatory Reform for Supersonic Flight")
- **HTML Cleaning**: Removes markup from Federal Register raw text

#### Executive Order Metadata Per Chunk:
```json
{
  "text": "The actual chunk content...",
  "chunk_type": "section",
  "section_title": "Sec. 2. Regulatory Reform for Supersonic Flight",
  "subsection": "(a)",
  "chunk_index": 4,
  "document_number": "2024-05678",
  "title": "Promoting Access to Voting",
  "executive_order_number": "14117",
  "president": "Biden",
  "signing_date": "2024-03-07",
  "summary": "Enhances federal efforts to promote access to voting...",
  "policy_topics": ["voting rights", "civil rights", "federal agencies"],
  "impacted_agencies": ["DOJ", "DHS", "VA"],
  "legal_authorities": ["52 U.S.C. § 20101"],
  "economic_sectors": ["government", "civic participation"]
}
```

### Processing Pipeline

**Supreme Court Opinions:**
1. **API Retrieval**: Fetch opinion and cluster data from CourtListener
2. **Opinion Type Detection**: Use regex patterns to identify different opinion types
3. **Section Parsing**: Detect Roman numeral sections and lettered subsections
4. **Intelligent Chunking**: Target 600 tokens, max 800 tokens while preserving legal structure
5. **Metadata Extraction**: Use GPT-5-nano for rich legal metadata
6. **Citation Formatting**: Build proper bluebook citations from cluster data
7. **Embedding Generation**: Create semantic embeddings for each chunk
8. **Database Storage**: Store chunks with complete metadata in Qdrant

**Executive Orders:**
1. **API Retrieval**: Fetch order data and raw text from Federal Register
2. **Structure Detection**: Identify header, sections, subsections, and tail blocks
3. **HTML Cleaning**: Remove markup and extract clean text
4. **Intelligent Chunking**: Target 300 tokens, max 400 tokens with sentence overlap
5. **Metadata Extraction**: Use GPT-5-nano for policy metadata
6. **API Metadata**: Extract signing date, president, agencies from API response
7. **Embedding Generation**: Create semantic embeddings for each chunk
8. **Database Storage**: Store chunks with complete metadata in Qdrant

## Government Data Sources

### Supreme Court Opinions
- **Source**: CourtListener API (Free Law Project)
- **Coverage**: Comprehensive collection of SCOTUS opinions from 1900+
- **API**: `https://www.courtlistener.com/api/rest/v4/`
- **Rate Limit**: 0.1 second delay between requests
- **Authentication**: Free API token required

### Executive Orders
- **Source**: Federal Register API
- **Coverage**: All presidential Executive Orders by date range
- **API**: `https://www.federalregister.gov/api/v1/`
- **Rate Limit**: 1.1 second delay (60 requests/minute limit)
- **Authentication**: No API key required

## Configuration

The system is configured through environment variables in `.env`:

```bash
# Required API keys
OPENAI_API_KEY="your-openai-api-key"
COURT_LISTENER_API_TOKEN="your-courtlistener-token"

# Optional (planned for future use)
FEDERAL_REGISTER_API_TOKEN="optional-token"
CONGRESS_GOV_API_TOKEN="optional-token"
```

**Chunking Parameters** (configurable in processor initialization):
- SCOTUS: target_chunk_size=600, max_chunk_size=800
- Executive Orders: target_chunk_size=300, max_chunk_size=400
- Rate limiting delays and collection names

## Development

### Code Quality
```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Type checking
uv run mypy src/

# Run tests
uv run pytest tests/
```

### Running Individual Components
```bash
# Test specific processor
uv run python -c "from governmentreporter.processors import SCOTUSOpinionProcessor; print('Import successful')"

# Check API connectivity
uv run python -c "from governmentreporter.apis import CourtListenerClient; client = CourtListenerClient(); print(f'Total opinions: {client.get_scotus_opinion_count()}')"
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
- 16GB RAM (recommended for large-scale processing)
- 5GB free storage (metadata-only approach keeps storage minimal)
- Stable internet connection for API access
- macOS with uv package manager support

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

**Note**: This project is designed for research and educational purposes.
